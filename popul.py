import streamlit as st
import pandas as pd
import requests
import bcrypt

st.set_page_config(layout='wide', page_icon=":beer:", page_title="Outil d’analyse Bousole des personnalités")

###### TO DO : CATEGORY WHEN USER IS VIGIE

# --- AUTHENTICATION LOGIC ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

users = st.secrets.get('users', {})
roles = st.secrets.get('roles', {})

def login_form():
    st.title('Connexion requise')
    with st.form('login_form'):
        username = st.text_input('Nom d\'utilisateur')
        password = st.text_input('Mot de passe', type='password')
        submit = st.form_submit_button('Se connecter')
        if submit:
            if username in users:
                hashed = users[username].encode()
                if bcrypt.checkpw(password.encode(), hashed):
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = username
                    st.session_state['role'] = roles.get(username, 'Vigie')
                    st.success('Connecté avec succès !')
                    st.rerun()
                else:
                    st.error('Nom d\'utilisateur ou mot de passe incorrect.')
            else:
                st.error('Nom d\'utilisateur ou mot de passe incorrect.')

if not st.session_state['authenticated']:
    login_form()
    st.stop()
# --- END AUTHENTICATION LOGIC ---

try:
    st.image("jelly.png", use_container_width=True)
except:
    st.image("jelly.png", use_column_width=True)

def fetch_dys_from_api(api_url):
    response = requests.get(api_url)
    response.raise_for_status()
    response.cookies.clear()
    themes_and_planets_data = response.json()

    # Transform the JSON data into a pandas DataFrame
    data_list = []
    for family in themes_and_planets_data.get('families', []):
        family_id = family.get('id')
        family_title = family.get('title')
        family_description = family.get('description')
        for dysfunction in family.get('dysfunctions', []):
            dysfunction_id = dysfunction.get('id')
            dysfunction_label = dysfunction.get('label')
            dysfunction_weight = dysfunction.get('weight')
            dysfunction_explanation = dysfunction.get('explanation')
            for question in dysfunction.get('questions', []):
                question_id = question.get('id')
                question_label = question.get('label')
                question_response_options = question.get('responseOptions')
                question_response_trigger = question.get('responseTrigger')
                data_list.append({
                    'family_id': family_id,
                    'family_title': family_title,
                    'family_description': family_description,
                    'dysfunction_id': dysfunction_id,
                    'dysfunction_label': dysfunction_label,
                    'dysfunction_weight': dysfunction_weight,
                    'dysfunction_explanation': dysfunction_explanation,
                    'question_id': question_id,
                    'question_label': question_label,
                    'question_response_options': question_response_options,
                    'question_response_trigger': question_response_trigger
                })

    df_themes_and_planets = pd.DataFrame(data_list)
    return df_themes_and_planets


DATABASE_URL = st.secrets["DATABASE_URL"]
DATABASE_API_KEY = st.secrets["DATABASE_API_KEY"]
api_prefix = st.secrets["api_prefix"]

def fetch_results_from_database():
    url = f"{DATABASE_URL}/rest/v1/new_dysfunctions" #
    headers = {
        "apikey": DATABASE_API_KEY,
        "Authorization": f"Bearer {DATABASE_API_KEY}",
        "Content-Type": "application/json",
    }
    params = {
        "select":   "id, dysfonctionnement, impact, exemple, thématique, solutions"
    }
    response = requests.get(url, headers=headers, params=params)
    print(response.status_code, response.text)
    response.raise_for_status()
    return response.json()


def insert_dysfunction_to_database(dys, impact, exemple, solutions, category):
    url = f"{DATABASE_URL}/rest/v1/new_dysfunctions"
    headers = {
        "apikey": DATABASE_API_KEY,
        "Authorization": f"Bearer {DATABASE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    payload = {
        "dysfonctionnement": dys,
        "impact": impact,
        "exemple": exemple,
        "solutions": solutions,
        "thématique": category
    }
    response = requests.post(url, headers=headers, json=payload)
    print(response.status_code, response.text)
    response.raise_for_status()
    return response.json()

data = fetch_results_from_database()

stars =["Collaborer en équipe", "Mesurer la vision produit"]
theme_is_new = False

st.title("Alimentation des dysfonctionnements")
if st.session_state.get('role') == 'Argios':
    st.header("Commencez par choisir une thématique")
    category = st.selectbox(
        "Choisir la thématique de l'e-diag",
        stars,
        index=None,
        placeholder="Choisissez une thématique ou renseignez une nouvelle thématique",
        accept_new_options=True,
    )
    st.write("You selected:", category)

if st.session_state.get('role') == 'Vigie':
    category = "Ajouté par Vigie"

if category == "Collaborer en équipe":
    api_url = f"{api_prefix}/1" 
elif category == "Mesurer la vision produit":
    api_url = f"{api_prefix}/2" 
else:
    theme_is_new = True

# Only Argios can see the dataframes
if st.session_state.get('role') == 'Argios':
    if theme_is_new == False:
        st.header(f"Les dysfonctionnements qui sont présents dans le e-diag pour {category}")
        df_themes_and_planets = fetch_dys_from_api(api_url)
        df_themes_and_planets.drop(columns=["family_id","dysfunction_id","dysfunction_weight","question_id","question_label","question_response_options","question_response_trigger"], inplace=True)
        df_themes_and_planets.drop_duplicates(subset="dysfunction_label",inplace=True)
        st.dataframe(data=df_themes_and_planets)
    else:
        st.write(f"Il n'y a pas encore de e-diag pour {category}")
    st.header("Les dysfonctionnements/modifications qui ne sont pas encore dans le e-diag")
    st.dataframe(data = data)

username = st.session_state.get('username', '')

st.header("Renseigner un dysfonctionnement")
dys = st.text_input("Le dysfonctionnement")
impact = st.text_input("L'impact")
exemple = st.text_input("Un exemple")
solutions = st.text_area("Solutions")
saved_category = f"{username}_{category}"

submit = st.button('Ajouter le dysfonctionnement')
if 'dys_posted' not in st.session_state:
    st.session_state['dys_posted'] = False

if submit:
    if st.session_state['dys_posted']:
        st.warning('Le dysfonctionnement a déjà été envoyé pour cette session.', icon='⚠️')
    else:
        try:
            insert_dysfunction_to_database(dys, impact, exemple, solutions, saved_category)
            st.success('Dysfonctionnement ajouté avec succès !')
            st.session_state['dys_posted'] = True
        except Exception as e:
            st.error(f"Erreur lors de l’ajout : {e}")