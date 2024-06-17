import streamlit as st
import sqlite3
import pandas as pd
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.utils import ImageReader
from fpdf import FPDF

# Initialize the SQLite database
def init_db():
    conn = sqlite3.connect('form_data.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS forms (
            id TEXT PRIMARY KEY,
            user_name TEXT,
            user_email TEXT,
            user_signature BLOB,
            user_score INTEGER,
            second_user_name TEXT,
            second_user_email TEXT,
            second_user_signature BLOB,
            second_user_score INTEGER
        )
    ''')

    existing_columns = [col[1] for col in c.execute('PRAGMA table_info(forms)').fetchall()]
    if 'user_email' not in existing_columns:
        c.execute('ALTER TABLE forms ADD COLUMN user_email TEXT')
    if 'second_user_email' not in existing_columns:
        c.execute('ALTER TABLE forms ADD COLUMN second_user_email TEXT')

    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    c.execute('''
        INSERT OR IGNORE INTO admins (username, password)
        VALUES (?, ?)
    ''', ('admin', 'password'))

    conn.commit()
    conn.close()
def generate_unique_link():
    unique_id = str(uuid.uuid4())
    return f"https://mysignature.streamlit.app/?id={unique_id}", unique_id

def save_data(unique_id, data):
    conn = sqlite3.connect('form_data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO forms (id, user_name, user_email, user_signature, user_score, second_user_name, second_user_email, second_user_signature, second_user_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (unique_id, data.get('user_name'), data.get('user_email'), data.get('user_signature'), data.get('user_score'),
          data.get('second_user_name'), data.get('second_user_email'), data.get('second_user_signature'), data.get('second_user_score')))
    conn.commit()
    conn.close()

def get_data(unique_id):
    conn = sqlite3.connect('form_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM forms WHERE id = ?', (unique_id,))
    data = c.fetchone()
    conn.close()
    if data:
        return {
            'id': data[0],
            'user_name': data[1],
            'user_email': data[2],
            'user_signature': data[3],
            'user_score': data[4],
            'second_user_name': data[5],
            'second_user_email': data[6],
            'second_user_signature': data[7],
            'second_user_score': data[8]
        }
    return None

def get_all_data():
    conn = sqlite3.connect('form_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM forms')
    data = c.fetchall()
    conn.close()
    return data

def update_data(unique_id, data):
    conn = sqlite3.connect('form_data.db')
    c = conn.cursor()
    c.execute('''
        UPDATE forms
        SET second_user_name = ?, second_user_email = ?, second_user_signature = ?, second_user_score = ?
        WHERE id = ?
    ''', (data.get('second_user_name'), data.get('second_user_email'), data.get('second_user_signature'), data.get('second_user_score'), unique_id))
    conn.commit()
    conn.close()

def send_email(to_email, link):
    from_email = 'shsmodernhill@shb.sch.id'
    from_password = 'jvvmdgxgdyqflcrf' 
    
    subject = "Complete the Form"
    body = f"Please complete the form by clicking the following link: {link}"
    
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(e)
        return False

def generate_pdf(signature_image, sender_name):
    pdf_buffer = BytesIO()
    c = pdf_canvas.Canvas(pdf_buffer, pagesize=letter)
    c.drawString(100, 700, f"Signed by: {sender_name}")
    
    img_temp = BytesIO()
    signature_image.save(img_temp, format='PNG')
    img_temp.seek(0)
    c.drawImage(ImageReader(img_temp), 100, 100, width=300, height=100)

    c.save()
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes

def create_pdf(data):
    pdf_buffer = BytesIO()
    c = pdf_canvas.Canvas(pdf_buffer, pagesize=letter)
    c.drawString(100, 750, "Form Response")
    
    y = 700
    for key, value in data.items():
        if key.endswith('signature'):
            img_temp = BytesIO(value)
            img_temp.seek(0)
            c.drawImage(ImageReader(img_temp), 100, y-100, width=300, height=100)
            y -= 150
        else:
            c.drawString(100, y, f"{key}: {value}")
            y -= 50

    c.save()
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes

def send_pdf_via_email(to_email, pdf_data, pdf_filename):
    from_email = 'shsmodernhill@shb.sch.id'
    from_password = 'jvvmdgxgdyqflcrf' 
    
    subject = "Form Response PDF"
    body = "Please find the attached PDF containing the form response."
    
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    attachment = MIMEBase('application', 'octet-stream')
    attachment.set_payload(pdf_data)
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
    msg.attach(attachment)
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(e)
        return False

def sign_up(username, password):
    conn = sqlite3.connect('form_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO admins (username, password) VALUES (?, ?)', (username, password))
    conn.commit()
    conn.close()

# Home page
def home():
    st.title("User Signature and Data Form")

    # Parse the query parameters from the URL
    query_params = st.experimental_get_query_params()  # Accessing as an attribute, not as a callable
    # Use st.experimental_get_query_params until st.query_params becomes available

    if "id" in query_params:
        unique_id = query_params["id"][0]
        if get_data(unique_id):
            second_user_form(unique_id)
        else:
            st.error("Invalid or expired link.")
    else:
        first_user_form()

def first_user_form():
    st.header("Step 1: Fill in your details, signature, and score")

    user_name = st.text_input("Your Name")
    user_email = st.text_input("Your Email")
    user_score = st.number_input("Your Score", min_value=0, max_value=100, step=1)
    second_user_email = st.text_input("Second User's Email")

    st.write("Draw your signature below:")
    user_signature_canvas = st_canvas(
        fill_color="rgb(255, 255, 255)",
        stroke_width=2,
        stroke_color="rgb(0, 0, 0)",
        background_color="rgb(240, 240, 240)",
        update_streamlit=True,
        height=150,
        width=400,
        drawing_mode="freedraw",
        key="first_user_signature",
    )

    if st.button("Generate Link for Second User"):
        if user_name and user_email and user_signature_canvas.image_data is not None and user_score is not None and second_user_email:
            user_signature_image = Image.fromarray(user_signature_canvas.image_data.astype('uint8'), 'RGBA')
            user_signature_bytes = BytesIO()
            user_signature_image.save(user_signature_bytes, format='PNG')
            user_signature_bytes = user_signature_bytes.getvalue()
            
            initial_data = {
                "user_name": user_name,
                "user_email": user_email,
                "user_signature": user_signature_bytes,
                "user_score": user_score,
                "second_user_name": None,
                "second_user_email": second_user_email,
                "second_user_signature": None,
                "second_user_score": None
            }
            link, unique_id = generate_unique_link()
            save_data(unique_id, initial_data)
            st.success(f"Link generated: {link}")
            if send_email(second_user_email, link):
                st.success("Email sent to the second user successfully!")
            else:
                st.error("Failed to send email to the second user.")
        else:
            st.error("Please fill in all the details and draw your signature.")

def second_user_form(unique_id):
    st.header("Step 2: Fill in your details, signature, and score")

    second_user_name = st.text_input("Your Name")
    second_user_email = st.text_input("Your Email")
    second_user_score = st.number_input("Your Score", min_value=0, max_value=100, step=1)

    st.write("Draw your signature below:")
    second_user_signature_canvas = st_canvas(
        fill_color="rgb(255, 255, 255)",
        stroke_width=2,
        stroke_color="rgb(0, 0, 0)",
        background_color="rgb(240, 240, 240)",
        update_streamlit=True,
        height=150,
        width=400,
        drawing_mode="freedraw",
        key="second_user_signature",
    )

    if st.button("Submit"):
        if second_user_name and second_user_email and second_user_signature_canvas.image_data is not None and second_user_score is not None:
            second_user_signature_image = Image.fromarray(second_user_signature_canvas.image_data.astype('uint8'), 'RGBA')
            second_user_signature_bytes = BytesIO()
            second_user_signature_image.save(second_user_signature_bytes, format='PNG')
            second_user_signature_bytes = second_user_signature_bytes.getvalue()
            
            updated_data = {
                "second_user_name": second_user_name,
                "second_user_email": second_user_email,
                "second_user_signature": second_user_signature_bytes,
                "second_user_score": second_user_score
            }
            update_data(unique_id, updated_data)
            st.success("Form completed and saved!")

            # Send PDF to both users
            final_data = get_data(unique_id)
            first_user_email = final_data['user_email']
            second_user_email = final_data['second_user_email']
            pdf_data = create_pdf(final_data)
            
            if send_pdf_via_email(first_user_email, pdf_data, f"form_response_{unique_id}.pdf") and send_pdf_via_email(second_user_email, pdf_data, f"form_response_{unique_id}.pdf"):
                st.success("PDF sent to both users successfully!")
            else:
                st.error("Failed to send PDF to users.")
        else:
            st.error("Please fill in all the details and draw your signature.")

def admin():
    st.title("Admin Page")

    admin_user = st.text_input("Username")
    admin_pass = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        signupuser = st.text_input("Create Username")
        signuppass = st.text_input("Create Password", type="password")
        
        sign_up(signupuser, signuppass)
        st.success("User Successfully Added")

    if st.button("Login"):
        if admin_user == "admin" and admin_pass == "password":
            st.success("Logged in as admin")
            data = get_all_data()
            if data:
                df = pd.DataFrame(data, columns=['ID', 'User Name', 'User Email', 'User Signature', 'User Score', 'Second User Name', 'Second User Email', 'Second User Signature', 'Second User Score'])
                st.dataframe(df)

                # Download as Excel
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                buffer.seek(0)
                st.download_button(label="Download Excel", data=buffer, file_name="responses.xlsx", mime="application/vnd.ms-excel")

                # Download as PDF
                pdf_buffer = BytesIO()
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="Form Responses", ln=True, align='C')
                
                for i, row in df.iterrows():
                    pdf.ln(10)
                    for key, value in row.items():
                        if key.endswith('signature'):
                            pdf.cell(200, 10, txt=f"{key}: [Signature Image]", ln=True, align='L')
                        else:
                            pdf.cell(200, 10, txt=f"{key}: {value}", ln=True, align='L')

                pdf_output = pdf.output(dest='S').encode('latin1')
                pdf_buffer.write(pdf_output)
                pdf_buffer.seek(0)
                st.download_button(label="Download PDF", data=pdf_buffer, file_name="responses.pdf", mime="application/pdf")

                # Send PDFs to recipients
                if st.button("Send PDFs to Recipients"):
                    for i, row in df.iterrows():
                        user_email = row['User Email']
                        pdf_data = create_pdf(row.to_dict())
                        send_pdf_via_email(user_email, pdf_data, f"form_response_{row['ID']}.pdf")
                    st.success("PDFs sent successfully!")

                # Send PDF to individual second users
                selected_user = st.selectbox("Select Second User to Send PDF", df['Second User Email'])
                if st.button("Send PDF to Selected Second User"):
                    row = df[df['Second User Email'] == selected_user].iloc[0]
                    pdf_data = create_pdf(row.to_dict())
                    if send_pdf_via_email(selected_user, pdf_data, f"form_response_{row['ID']}.pdf"):
                        st.success(f"PDF sent to {selected_user} successfully!")
                    else:
                        st.error(f"Failed to send PDF to {selected_user}.")
            else:
                st.warning("No data found.")
        else:
            st.error("Invalid credentials.")

# Main function with sidebar navigation
def main():
    init_db()
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Admin"])
    
    if page == "Home":
        home()
    elif page == "Admin":
        admin()

if __name__ == "__main__":
    main()
