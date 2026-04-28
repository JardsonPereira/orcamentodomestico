import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import base64
import os

# --- CONFIGURAÇÃO DA LOGO ---
# Certifique-se de que o arquivo no GitHub se chama exatamente logo.png
ARQUIVO_LOGO = "logo.png"

def get_base64_img(img_path):
    """Converte a imagem local para Base64 para garantir o ícone no celular"""
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{data}"
    except:
        return None
    return None

# --- CONEXÃO SEGURA SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro nas credenciais do Supabase. Verifique os Secrets.")
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
    # 1. Carregar os dados da logo para o ícone
    logo_data = get_base64_img(ARQUIVO_LOGO)

    # 2. CONFIGURAÇÃO DA PÁGINA (Sempre o primeiro comando do Streamlit)
    st.set_page_config(
        page_title="ContabilApp Pro",
        layout="wide",
        page_icon=ARQUIVO_LOGO if os.path.exists(ARQUIVO_LOGO) else "💰"
    )

    # 3. INJEÇÃO DE METADADOS PARA ÍCONE NO CELULAR (PWA Style)
    if logo_data:
        st.markdown(f"""
            <head>
                <link rel="apple-touch-icon" href="{logo_data}">
                <link rel="icon" sizes="192x192" href="{logo_data}">
                <link rel="icon" sizes="512x512" href="{logo_data}">
                <meta name="mobile-web-app-capable" content="yes">
                <meta name="apple-mobile-web-app-status-bar-style" content="default">
            </head>
        """, unsafe_allow_html=True)

    # 4. CSS PERSONALIZADO
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            html, body, [class*="st-"] {{ font-family: 'Inter', sans-serif; }}
            .stApp {{ background-color: #F0F2F5; }}
            .stButton>button {{ width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; background-color: #007BFF; color: white; }}
            [data-testid="stExpander"], div[data-testid="stForm"], .stContainer {{ 
                background: white; border-radius: 12px; border: 1px solid #eee; padding: 15px; margin-bottom: 10px;
            }}
        </style>
    """, unsafe_allow_html=True)

    # --- LÓGICA DE NAVEGAÇÃO ---
    if not st.session_state.logado:
        # Exibição da Logo na tela de login
        if os.path.exists(ARQUIVO_LOGO):
            _, col_logo, _ = st.columns([1, 1, 1])
            with col_logo:
                st.image(ARQUIVO_LOGO, width=150)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        with col_central:
            escolha = st.radio("Acesso", ["Entrar na Conta", "Criar Nova Conta"], horizontal=True, label_visibility="collapsed")
            
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
                        except:
                            st.error("E-mail ou senha incorretos.")
                            
                elif escolha == "Criar Nova Conta":
                    st.subheader("Cadastro")
                    novo_nome = st.text_input("Seu Nome")
                    novo_email = st.text_input("E-mail").strip()
                    nova_senha = st.text_input("Crie uma senha", type='password')
                    
                    if st.button("CRIAR MINHA CONTA"):
                        try:
                            res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                            if res.user:
                                st.session_state.user_name = novo_nome
                                st.success("Conta criada! Agora faça o login.")
                        except Exception as e:
                            st.error(f"Erro ao cadastrar: {str(e)}")

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

        # BUSCA DE DADOS NO SUPABASE
        try:
            res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
            lista_cartoes = [item['card_name'] for item in res_c.data]
            dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
            
            res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(res_f.data)
        except:
            st.error("Erro ao carregar dados do banco.")
            st.stop()

        tab_lanc, tab_extrato, tab_cartao, tab_config = st.tabs(["➕ Lançar", "📊 Extrato", "💳 Cartões", "🛠️ Ajustes"])

        with tab_lanc:
            st.subheader("Nova Movimentação")
            metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
            cart_v = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes: cart_v = st.selectbox("Qual Cartão?", lista_cartoes)
                else: st.warning("Cadastre um cartão em 'Ajustes' primeiro.")

            with st.form("form_lanca", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                desc = st.text_input("Descrição")
                valor_t = st.number_input("Valor (R$)", min_value=0.01, step=0.10)
                data_o = st.date_input("Data", datetime.now())
                total_p = 1
                if metodo_sel == "Cartão de Crédito":
                    total_p = st.number_input("Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 SALVAR LANÇAMENTO"):
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
                    st.success("✅ Lançado com sucesso!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                mes_sel = st.radio("Selecione o Mês", meses, index=len(meses)-1, horizontal=True)
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                rec = f[f['type'] == 'Receita']['amount'].sum()
                des = f[f['type'] == 'Despesa']['amount'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {rec:,.2f}")
                c2.metric("Despesas", f"R$ {des:,.2f}")
                c3.metric("Saldo", f"R$ {rec-des:,.2f}", delta=float(rec-des))
                
                st.dataframe(f[['date', 'category', 'amount', 'payment_method']], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum dado encontrado para este usuário.")

        with tab_config:
            st.subheader("Configurações do Sistema")
            novo_c = st.text_input("Nome do Novo Cartão")
            if st.button("Adicionar Cartão"):
                if novo_c:
                    supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": novo_c}).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
