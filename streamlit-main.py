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

# Generate dynamic prompt based on user input
def build_dynamic_prompt(data, custom_prompt_template, word_count):
    """Build prompt using user-provided template with data substitution"""
    safeClinicName = find_value_by_possible_keys(data, ["name", "Name", "clinicName"]) or "Clinic"
    clinicMainSpecialty = find_value_by_possible_keys(data, ["specialty", "Specialty", "mainSpecialty"]) or "Healthcare"
    clinicSubSpecialties = find_value_by_possible_keys(data, ["subSpecialties", "SubSpecialties"]) or clinicMainSpecialty
    clinicAbout = find_value_by_possible_keys(data, ["about", "About", "description", "Description"]) or "Not provided"
    clinicLocation = find_value_by_possible_keys(data, ["location", "city", "county", "country", "address"]) or "Kenya"
    clinicContact = find_contact_info(data)

    # Create substitution variables for the template
    template_vars = {
        'clinic_name': safeClinicName,
        'main_specialty': clinicMainSpecialty,
        'sub_specialties': clinicSubSpecialties,
        'about': clinicAbout,
        'location': clinicLocation,
        'word_count': word_count,
        'email': clinicContact.get('email', ''),
        'phone': clinicContact.get('phone', ''),
        'website': clinicContact.get('website', '')
    }
    
    # Replace template variables in the custom prompt
    try:
        formatted_prompt = custom_prompt_template.format(**template_vars)
        return formatted_prompt
    except KeyError as e:
        return f"Error in prompt template: Missing variable {e}. Available variables: {list(template_vars.keys())}"

def get_default_prompt_template():
    """Return the default prompt template with placeholders"""
    return """Consider yourself as a professional medical SEO content writer. Create an SEO-optimized content about {clinic_name} strictly based on the following data. Do not cook and fabricate details beyond logical extensions of specialties explicitly tied to the data. Use only the provided data with reference to the context below.

Clinic Data:
Clinic Name: {clinic_name}
Location: {location}
Main Specialty: {main_specialty}
Subspecialties: {sub_specialties}
About: {about}
Email: {email}
Phone: {phone}
Website: {website}

STRICT Requirements:
Word Count: The content MUST be exactly {word_count} words.
Structure: Distribute words exactly (~140 intro, ~140 expertise, ~140 services, ~80 booking).

Writing Style Rules:
Always write in 3rd person.
Do NOT use "we", "us", "our".
Do NOT introduce with "Here's the SEO content…" or "Welcome to…".
Maintain neutral, factual tone.

Keyword Frequency, Highlighting & Linking:
Limit each key term ("{main_specialty}", "NHIF") to 4–5 uses.
Use <strong> ONLY for: "{clinic_name}", "{main_specialty}", "NHIF", "maternity", "Caesarean", "Obstetrics", "pregnancy", "delivery", "contraception", "menopause", "prenatal care", "family planning", "cervical screening", "Maternal and Child Health", "Reproductive Health".
Do NOT bold unlisted terms.

Hyperlinking Rules:
- Link "aesthetic EMR software" → https://www.easyclinic.io/aesthetic-emr-software/
- Link "clinic software features" → https://www.easyclinic.io/features/
- Link "EasyClinic" → https://www.easyclinic.io/
- Link "pricing plans" → https://www.easyclinic.io/pricing/
Use each link once only.

Integration of Generic Queries:
Intro: Answer "Which is the best clinic near me?" and "Where can I find a trusted clinic in {location}?" Include EasyClinic link.
Expertise: Answer "What clinic offers affordable treatment in {main_specialty}?" Include clinic software features link.
Services: Answer "Clinics offering <strong>{main_specialty}</strong> in {location}" Include aesthetic EMR software link.
Booking: Answer "Best private clinic near me" Include pricing plans link.

Section Breakdown:
Introduction (~140 words) <p>...</p>
Expertise (~140 words) <h2>Expertise and Facilities</h2><ul><li>...</li></ul>
Services (~140 words) <h2>{main_specialty} Services Offered by {clinic_name}</h2><ul><li>...</li></ul>
Booking (~80 words) <h2>Book an Appointment with {clinic_name}</h2><p>... end with contact information</p>
"""

# --- Streamlit App ---
st.title("🏥 Clinic SEO Content Generator")

# Initialize session state for prompt template
if "prompt_template" not in st.session_state:
    st.session_state["prompt_template"] = get_default_prompt_template()

left_col, right_col = st.columns([2, 1])

with left_col:
    st.write("Upload a JSON file to generate SEO-optimized content with your custom prompt.")
    
    # Only JSON upload - removed manual entry
    uploaded_file = st.file_uploader("Upload Clinic Data JSON", type=["json"])
    data = {}
    if uploaded_file:
        data = json.load(uploaded_file)
        if isinstance(data, list):
            st.warning("Multiple records found. Using the first record only.")
            data = data[0]  # Take first record if multiple exist
        
        # Show preview of loaded data
        st.subheader("📋 Loaded Data Preview")
        st.json(data)
    
    word_count = st.number_input("Word Count", min_value=500, max_value=800, value=500, step=10)
    
    if st.button("Generate SEO Content") and data:
        with st.spinner("Generating SEO content with Gemini..."):
            # Use the current prompt template from session state
            prompt = build_dynamic_prompt(data, st.session_state["prompt_template"], word_count)
            
            if prompt.startswith("Error"):
                st.error(prompt)
            else:
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
    st.subheader("📝 Dynamic Prompt Editor")
    
    # Reset to default button
    if st.button("🔄 Reset to Default Template"):
        st.session_state["prompt_template"] = get_default_prompt_template()
        st.rerun()
    
    # Custom prompt editor
    st.session_state["prompt_template"] = st.text_area(
        "Edit Prompt Template",
        value=st.session_state["prompt_template"],
        height=400,
        help="Use {variable_name} placeholders. Available variables: clinic_name, main_specialty, sub_specialties, about, location, word_count, email, phone, website"
    )
    
    # Show available variables
    st.subheader("📋 Available Variables")
    variables = [
        "clinic_name", "main_specialty", "sub_specialties", 
        "about", "location", "word_count", "email", "phone", "website"
    ]
    for var in variables:
        st.code(f"{{{var}}}")
    
    st.caption("💡 Modify the prompt template above to customize how the AI generates content. Use curly braces {} around variable names for dynamic substitution.")