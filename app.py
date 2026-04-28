import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import os

# --- CONFIGURAÇÃO DA LOGO LOCAL ---
# Certifique-se de que o nome abaixo é exatamente igual ao do ficheiro na pasta
NOME_DO_FICHEIRO_LOGO = "logo.png" 

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro nas credenciais. Verifique os Secrets no Streamlit Cloud.")
    st.stop()

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_name" not in st.session_state:
    st.session_state.user_name = "Usuário"
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    # 1. O PRIMEIRO COMANDO DEVE SER O SET_PAGE_CONFIG
    # Verificamos se o ficheiro existe para evitar erros
    if os.path.exists(NOME_DO_FICHEIRO_LOGO):
        icone = NOME_DO_FICHEIRO_LOGO
    else:
        icone = "💰"

    st.set_page_config(
        page_title="ContabilApp Pro", 
        layout="wide", 
        page_icon=icone
    )
    
    # 2. INJEÇÃO DE CSS E HTML (Com chaves duplicadas para f-string)
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            html, body, [class*="st-"] {{ font-family: 'Inter', sans-serif; }}
            .stApp {{ background-color: #F0F2F5; }}
            .stButton>button {{ width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; }}
            [data-testid="stExpander"], div[data-testid="stForm"], .stContainer {{ 
                background: white; border-radius: 12px; border: 1px solid #eee; padding: 15px; margin-bottom: 10px;
            }}
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.logado:
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        _, col_central, _ = st.columns([1, 2, 1])
        
        with col_central:
            escolha = st.radio("Acesso", ["Entrar na Conta", "Criar Nova Conta", "Recuperar Senha"], horizontal=True, label_visibility="collapsed")
            
            with st.container():
                if escolha == "Entrar na Conta":
                    st.subheader("Login")
                    email_login = st.text_input("E-mail", placeholder="seu@email.com").strip()
                    senha_login = st.text_input("Senha", type='password')
                    
                    if st.button("ACESSAR SISTEMA"):
                        try:
                            response = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                            if response.user:
                                st.session_state.logado = True
                                st.session_state.user_email = email_login
                                st.rerun()
                        except Exception as e:
                            st.error("E-mail ou senha incorretos.")
                            
                elif escolha == "Criar Nova Conta":
                    st.subheader("Cadastro")
                    novo_nome = st.text_input("Seu Nome", placeholder="Ex: Jardson")
                    novo_email = st.text_input("E-mail", placeholder="seu@email.com").strip()
                    nova_senha = st.text_input("Crie uma senha", type='password', placeholder="mínimo 6 caracteres")
                    
                    if st.button("CRIAR MINHA CONTA"):
                        if not novo_nome or not novo_email or len(nova_senha) < 6:
                            st.warning("Preencha todos os campos corretamente.")
                        else:
                            try:
                                res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                                if res.user:
                                    st.session_state.user_name = novo_nome
                                    st.success("Conta criada! Agora faça o login.")
                            except Exception as e:
                                st.error(f"Erro ao cadastrar: {str(e)}")

                else:
                    st.subheader("Recuperação")
                    email_rec = st.text_input("Digite seu e-mail").strip()
                    if st.button("ENVIAR LINK"):
                        try:
                            supabase.auth.reset_password_for_email(email_rec)
                            st.success("Link enviado! Verifique seu e-mail.")
                        except Exception as e:
                            st.error(f"Erro: {str(e)}")

    else:
        # --- SISTEMA LOGADO ---
        col_title, col_user = st.columns([3, 1])
        with col_title:
            st.title(f"💰 Olá, {st.session_state.get('user_name', 'Usuário')}")
        with col_user:
            with st.expander(f"👤 Perfil"):
                if st.button("Encerrar Sessão"):
                    st.session_state.logado = False
                    st.rerun()

        # DADOS DO SUPABASE
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs(["➕ Lançar", "📊 Extrato", "💳 Cartões", "⚙️ Editar", "🛠️ Ajustes"])

        with tab_lanc:
            st.subheader("Nova Movimentação")
            metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
            cart_v = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes: cart_v = st.selectbox("Qual Cartão?", lista_cartoes)
                else: st.warning("Cadastre um cartão primeiro.")

            with st.form("form_lanca", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                desc = st.text_input("Descrição")
                valor_t = st.number_input("Valor (R$)", min_value=0.01, step=0.10)
                data_o = st.date_input("Data", datetime.now())
                total_p = 1
                if metodo_sel == "Cartão de Crédito":
                    total_p = st.number_input("Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 SALVAR"):
                    u_email = st.session_state.user_email
                    v_parc = valor_t / int(total_p)
                    for i in range(int(total_p)):
                        d_venc = add_months(data_o, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parc, 2), "date": d_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_sel, "card_name": cart_v,
                            "installment_total": int(total_p), "installment_number": i + 1
                        }).execute()
                    st.success("✅ Lançado!")
                    st.rerun()

        # ... (O restante do código das abas de Extrato e Gestão permanece o mesmo)

if __name__ == "__main__":
    main()
