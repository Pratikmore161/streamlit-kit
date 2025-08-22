import streamlit as st
import json
from google.generativeai import GenerativeModel, configure

# Configure Gemini API key
if 'GEMINI_API_KEY' not in st.secrets:
    st.error("Please set up your GEMINI_API_KEY in Streamlit secrets")
    st.stop()
    
configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize model
model = GenerativeModel("gemini-2.0-flash")

# Helper functions
def find_value_by_possible_keys(data, possible_keys):
    for key in possible_keys:
        if key in data and isinstance(data[key], str) and data[key].strip() != "":
            return data[key]
    return None

def find_contact_info(data):
    email_keys = ["email", "Email", "contact_email", "contactEmail"]
    phone_keys = ["phone", "Phone", "phoneNumber", "mobile"]
    website_keys = ["website", "Website", "url", "URL"]

    return {
        "email": find_value_by_possible_keys(data, email_keys),
        "phone": find_value_by_possible_keys(data, phone_keys),
        "website": find_value_by_possible_keys(data, website_keys),
    }

# Generate prompt
def build_prompt(data, word_count):
    safeClinicName = find_value_by_possible_keys(data, ["name", "Name", "clinicName"]) or "Clinic"
    clinicMainSpecialty = find_value_by_possible_keys(data, ["specialty", "Specialty", "mainSpecialty"]) or "Healthcare"
    clinicSubSpecialties = find_value_by_possible_keys(data, ["subSpecialties", "SubSpecialties"]) or clinicMainSpecialty
    clinicAbout = find_value_by_possible_keys(data, ["about", "About", "description", "Description"]) or "Not provided"
    clinicLocation = find_value_by_possible_keys(data, ["location", "city", "county", "country", "address"]) or "Kenya"
    clinicContact = find_contact_info(data)

    contactSection = f"<p>For inquiries, please contact <strong>{safeClinicName}</strong> <a href='#contact'>here</a></p>"
    if clinicContact["email"]:
        contactSection = f"<p>For inquiries, please contact <strong>{safeClinicName}</strong> at <a href='mailto:{clinicContact['email']}'>{clinicContact['email']}</a></p>"
    elif clinicContact["phone"]:
        contactSection = f"<p>For inquiries, please contact <strong>{safeClinicName}</strong> at {clinicContact['phone']}</p>"

    servicesHeader = f"<h2>{clinicMainSpecialty} Services Offered by {safeClinicName}</h2>"
    bookingHeader = f"<h2>Book an Appointment with {safeClinicName}</h2>"

    prompt = f"""
Consider yourself as a professional medical SEO content writer. Create an SEO-optimized content about {safeClinicName} strictly based on the following data. Do not cook and fabricate details beyond logical extensions of specialties explicitly tied to the data. Use only the provided data with reference to the context below.

Clinic Data:
Clinic Name: {safeClinicName}
Location: {clinicLocation}
Main Specialty: {clinicMainSpecialty}
Subspecialties: {clinicSubSpecialties}
About: {clinicAbout}
{f"- Email: {clinicContact['email']}" if clinicContact['email'] else ""}
{f"- Phone: {clinicContact['phone']}" if clinicContact['phone'] else ""}
{f"- Website: {clinicContact['website']}" if clinicContact['website'] else ""}

STRICT Requirements:
Word Count: The content MUST be exactly {word_count} words.
Structure: Distribute words exactly (~140 intro, ~140 expertise, ~140 services, ~80 booking).

Writing Style Rules:
Always write in 3rd person.
Do NOT use "we", "us", "our".
Do NOT introduce with “Here’s the SEO content…” or “Welcome to…”.
Maintain neutral, factual tone.

Keyword Frequency, Highlighting & Linking:
Limit each key term ("{clinicMainSpecialty}", "NHIF") to 4–5 uses.
Use <strong> ONLY for: "{safeClinicName}", "{clinicMainSpecialty}", "NHIF", "maternity", "Caesarean", "Obstetrics", "pregnancy", "delivery", "contraception", "menopause", "prenatal care", "family planning", "cervical screening", "Maternal and Child Health", "Reproductive Health".
Do NOT bold unlisted terms.

Hyperlinking Rules:
- Link “aesthetic EMR software” → https://www.easyclinic.io/aesthetic-emr-software/
- Link “clinic software features” → https://www.easyclinic.io/features/
- Link “EasyClinic” → https://www.easyclinic.io/
- Link “pricing plans” → https://www.easyclinic.io/pricing/
Use each link once only.

Integration of Generic Queries:
Intro: Answer “Which is the best clinic near me?” and “Where can I find a trusted clinic in {clinicLocation}?” Include EasyClinic link.
Expertise: Answer “What clinic offers affordable treatment in {clinicMainSpecialty}?” Include clinic software features link.
Services: Answer “Clinics offering <strong>{clinicMainSpecialty}</strong> in {clinicLocation}” Include aesthetic EMR software link.
Booking: Answer “Best private clinic near me” Include pricing plans link. End with {contactSection}.

Section Breakdown:
Introduction (~140 words) <p>...</p>
Expertise (~140 words) <h2>Expertise and Facilities</h2><ul><li>...</li></ul>
Services (~140 words) {servicesHeader}<ul><li>...</li></ul>
Booking (~80 words) {bookingHeader}<p>... end with {contactSection}</p>
"""
    return prompt

# --- Streamlit App ---
st.title("🏥 Clinic SEO Content Generator")

left_col, right_col = st.columns([2, 1])

with left_col:
    st.write("Enter clinic data or upload a JSON file to generate SEO-optimized content.")
    
    # Input method selection
    input_method = st.radio("Input Method:", ["Manual Entry", "Upload JSON"])
    
    data = {}
    if input_method == "Manual Entry":
        st.subheader("Enter Clinic Details")
        data["name"] = st.text_input("Clinic Name")
        data["specialty"] = st.text_input("Main Specialty")
        data["subSpecialties"] = st.text_input("Sub-specialties (comma-separated)")
        data["about"] = st.text_area("About the Clinic")
        data["location"] = st.text_input("Location")
        data["email"] = st.text_input("Email")
        data["phone"] = st.text_input("Phone")
        data["website"] = st.text_input("Website")
    else:
        uploaded_file = st.file_uploader("Upload Clinic Data JSON", type=["json"])
        if uploaded_file:
            data = json.load(uploaded_file)
            if isinstance(data, list):
                st.warning("Multiple records found. Using the first record only.")
                data = data[0]  # Take first record if multiple exist
    
    word_count = st.number_input("Word Count", min_value=500, max_value=800, value=500, step=10)
    
    if st.button("Generate SEO Content") and data:
        with st.spinner("Generating SEO content with Gemini..."):
            # Get the current prompt from the right column
            prompt = st.session_state.get("current_prompt", build_prompt(
                data,
                list(data.keys())[:5],  # First 5 keys as default headers
                word_count
            ))
            
            response = model.generate_content(prompt)
            content = response.text

        st.subheader("Generated SEO Content")
        st.markdown(content, unsafe_allow_html=True)

        if data.get('name'):
            st.download_button(
                "Download HTML",
                content,
                file_name=f"{data.get('name','clinic').replace(' ','-').lower()}-seo.html",
                mime="text/html"
            )

with right_col:
    st.subheader("📝 Prompt Editor")
    
    # Initialize default prompt in session_state if we have data
    if data:
        if "current_prompt" not in st.session_state:
            st.session_state["current_prompt"] = build_prompt(
                data,
                list(data.keys())[:5],  # First 5 keys as default headers
                word_count
            )
    
    # Custom prompt box
    custom_prompt = st.checkbox("Use custom prompt")
    
    if custom_prompt:
        prompt_text = st.text_area(
            "Edit Prompt",
            value=st.session_state.get("current_prompt", ""),
            height=400,
            key="current_prompt"
        )
    else:
        # Show read-only current prompt
        st.text_area(
            "Current Prompt",
            value=st.session_state.get("current_prompt", "No prompt generated yet."),
            height=400,
            disabled=True
        )
    
    st.caption("✏️ Check 'Use custom prompt' to edit the prompt before generating content.")
