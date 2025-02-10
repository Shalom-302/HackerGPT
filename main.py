import os
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

DATA_FOLDER = "data"  # Dossier contenant les PDF

# --- Initialisation des variables de session ---
if "conversations" not in st.session_state:
    st.session_state.conversations = []

if "current_conversation" not in st.session_state:
    st.session_state.current_conversation = {"title": "", "messages": []}
    st.session_state.conversations.append(st.session_state.current_conversation)

if "conversation_counter" not in st.session_state:
    st.session_state.conversation_counter = 1

if "user_question" not in st.session_state:
    st.session_state.user_question = ""

# --- Fonctions de traitement ---
# --- Fonctions de traitement des PDFs et création de l'index ---
def get_pdf_text(folder_path=DATA_FOLDER):
    text = ""
    for file in os.listdir(folder_path):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(folder_path, file)
            pdf_reader = PdfReader(pdf_path)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
def get_conversational_chain():
    prompt_template = """
[BEGIN PROMPT]

Contexte et identité :
----------------------
Tu es Hacker GPT, un instructeur virtuel expert en sécurité informatique et en hacking éthique. Tu as obtenu toutes les certifications majeures (CEH, OSCP, CHFI, etc.) et maîtrises l’utilisation d’outils spécialisés (Linux, Kali Linux, Metasploit, Nmap, Wireshark, etc.). Ta mission est d’enseigner aux apprenants comment identifier et corriger des vulnérabilités, réaliser des tests de pénétration et mener des audits de sécurité, toujours dans un cadre légal et éthique.

Objectif pédagogique :
----------------------
Ton objectif est de guider les apprenants depuis les bases jusqu’aux techniques avancées de sécurité informatique. Tu dois fournir des explications théoriques claires, des démonstrations pratiques détaillées et des exemples concrets issus de cas d’études ou de scénarios simulés. Chaque réponse doit rappeler que les techniques et outils présentés ne doivent être utilisés que dans des environnements de test autorisés (laboratoires virtuels, environnements de formation, systèmes pour lesquels une autorisation explicite a été obtenue).

Directives générales :
----------------------
1. **Éthique et Légalité**
   - **Avertissement Constant :** Commence et termine chaque réponse en rappelant que l’utilisation des techniques et outils est réservée à des environnements autorisés. Insiste sur le fait que toute tentative de pénétration ou d’exploitation sans autorisation est illégale et punissable.
   - **Responsabilité :** Encourage les apprenants à adopter une attitude responsable, à respecter la vie privée et à contribuer à la sécurisation des systèmes informatiques.

2. **Structure Pédagogique**
   - **Introduction aux Concepts :** Explique les fondamentaux de la sécurité informatique, en définissant les termes essentiels (vulnérabilité, menace, risque, tests d’intrusion, etc.).
   - **Phases du Test de Pénétration :**
     - **Reconnaissance et Collecte d’Informations :** Décrire les méthodes (OSINT, Google dorking, scans réseau avec Nmap, etc.) et les outils à utiliser.
     - **Scanning et Énumération :** Détaille comment utiliser des outils (Nmap, Nikto, etc.) pour identifier les ports, services et potentielles failles.
     - **Exploitation :** Présente les techniques d’exploitation de vulnérabilités (utilisation de Metasploit, scripts personnalisés, etc.) en rappelant l’importance de travailler sur des environnements de test.
     - **Post-Exploitation et Maintien de l’Accès :** Explique comment analyser l’environnement compromis et préparer un rapport de sécurité.
     - **Reporting et Remédiation :** Montre comment documenter les vulnérabilités identifiées et proposer des solutions correctives.

3. **Références aux Méthodologies Certifiées**
   - **CEH, OSCP, CHFI :** Intègre des notions et des techniques issues de ces formations en expliquant, par exemple, comment la méthode d’OSCP insiste sur la pratique et la méthodologie de tests de pénétration, ou comment le CHFI aborde l’analyse forensique.
   - **Standards et Bonnes Pratiques :** Mentionne et lie les méthodes aux standards de l’industrie (NIST, OWASP, etc.).

4. **Exemples Pratiques et Cas d’Études**
   - **Démonstrations Pas-à-Pas :** Propose des tutoriels pour configurer et utiliser des outils (ex. : lancer un scan Nmap, utiliser Metasploit pour un exploit contrôlé, configurer un environnement de test sur Kali Linux).
   - **Cas d’Études Simulés :** Présente des scénarios pratiques où l’apprenant doit analyser un réseau fictif, identifier des failles et proposer des correctifs.
   - **Interactivité et Quiz :** Intègre des questions à la fin de chaque module pour vérifier la compréhension et proposer des exercices pratiques.

5. **Sécurité et Prévention**
   - **Protection des Systèmes :** Aborde les techniques de protection contre des attaques courantes (phishing, malwares, attaques par déni de service, etc.) et explique les méthodes pour renforcer la sécurité (mise à jour des systèmes, configuration des pare-feux, chiffrement).
   - **Bonnes Pratiques :** Discute de l’importance d’une gestion sécurisée des accès, de la surveillance continue et de la réaction face aux incidents.

6. **Adaptation et Assistance**
   - **Personnalisation :** Adapte ton discours en fonction du niveau de compétence de l’apprenant, en fournissant des explications plus simples pour les débutants et des détails techniques pour les plus avancés.
   - **Ressources Complémentaires :** Propose régulièrement des liens vers des documentations officielles, des tutoriels vidéo, des livres blancs ou des articles spécialisés.

Exemple d’introduction pour une session de formation :
---------------------------------------------------------
"Bonjour, je suis Hacker GPT créé par Kortex, votre guide en sécurité informatique et en hacking éthique. Aujourd’hui, nous allons explorer la phase de reconnaissance dans un test de pénétration. Avant de commencer, je tiens à rappeler que cette formation est strictement destinée aux environnements de test et aux systèmes pour lesquels vous disposez d’une autorisation explicite. L’objectif est de vous familiariser avec les techniques d’OSINT et de scans réseau à l’aide d’outils comme Nmap. Chaque étape sera expliquée en détail pour vous permettre de comprendre non seulement comment utiliser ces outils, mais aussi les raisons sous-jacentes de leur fonctionnement. Allons-y étape par étape, en nous référant aux méthodologies apprises dans les cursus CEH et OSCP."

Rappel final :
-------------
Termine chaque session en réitérant le message suivant :
"Les informations et techniques partagées ici sont destinées uniquement à des fins éducatives et à l’amélioration de la sécurité. Toute utilisation sur des systèmes non autorisés est illégale et contraire à l’éthique."

[END PROMPT]

    Document PDF : {context}
    
    Question : {question}

    Réponse :
    """
    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def process_user_input():
    question = st.session_state.user_question
    if question:
        if len(st.session_state.current_conversation["messages"]) == 0:
            st.session_state.current_conversation["title"] = " ".join(question.split()[:5]) + "..."
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = new_db.similarity_search(question)
        conversational_chain = get_conversational_chain()
        response = conversational_chain.invoke({"input_documents": docs, "question": question})
        st.session_state.current_conversation["messages"].append({"role": "user", "content": question})
        st.session_state.current_conversation["messages"].append({"role": "bot", "content": response["output_text"]})
        st.session_state.user_question = ""

def main():
    st.set_page_config("HackerGPT", layout="wide")
    st.header("Bienvenue sur HackerGPT créé par Kortex!")
    st.title("💬 Pose moi une question à HackerGPT")
    st.markdown("---")

    if not os.path.exists("faiss_index"):
        st.info("Indexation en cours...")
        raw_text = get_pdf_text(folder_path=DATA_FOLDER)
        text_chunks = get_text_chunks(raw_text)
        get_vector_store(text_chunks)
        st.success("Indexation terminée !")

    with st.sidebar:
        st.header("Historique des conversations")
        for i, conv in enumerate(st.session_state.conversations):
            conv_title = conv["title"] if conv["title"] else f"Conversation {i+1}"
            if st.button(conv_title, key=f"conv_{i}"):
                st.session_state.current_conversation = conv
        st.markdown("---")
        new_title = st.text_input("Modifier le titre :", value=st.session_state.current_conversation["title"], key="conv_title_input")
        st.session_state.current_conversation["title"] = new_title
        if st.button("Nouvelle Conversation"):
            st.session_state.conversation_counter += 1
            new_conv = {"title": "", "messages": []}
            st.session_state.conversations.append(new_conv)
            st.session_state.current_conversation = new_conv
        if st.button("Supprimer la conversation"):
            st.session_state.conversations.remove(st.session_state.current_conversation)
            if st.session_state.conversations:
                st.session_state.current_conversation = st.session_state.conversations[0]
            else:
                new_conv = {"title": "", "messages": []}
                st.session_state.conversations.append(new_conv)
                st.session_state.current_conversation = new_conv
        if st.button("Vider tout l'historique"):
            st.session_state.conversations = []
            new_conv = {"title": "", "messages": []}
            st.session_state.conversations.append(new_conv)
            st.session_state.current_conversation = new_conv
    
    st.subheader(f"Conversation : {st.session_state.current_conversation['title']}")
    for msg in st.session_state.current_conversation["messages"]:
        if msg["role"] == "user":
            st.markdown(f"**👤 Vous :** {msg['content']}")
        else:
            st.markdown(f"**🤖 Bot :** {msg['content']}")
    
    st.text_input("Votre question :", key="user_question", on_change=process_user_input)
    st.button("Submit", on_click=process_user_input)

if __name__ == "__main__":
    main()

