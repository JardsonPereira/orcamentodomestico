import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONFIGURAÇÃO DA LOGO ---
# Coloque aqui o link da sua imagem PNG ou JPG hospedada na internet
LOGO_URL = "URL_DA_SUA_LOGO_AQUI" 

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
    # 1. O PRIMEIRO COMANDO DEVE SER ESTE:
    st.set_page_config(
        page_title="ContabilApp Pro", 
        layout="wide", 
        page_icon=LOGO_URL if LOGO_URL != "URL_DA_SUA_LOGO_AQUI" else "💰"
    )
    
    # 2. INJEÇÃO DE HTML PARA ÍCONE DE CELULAR E ESTILIZAÇÃO CSS
    st.markdown(f"""
        <head>
            <link rel="apple-touch-icon" href="{LOGO_URL}">
            <link rel="icon" sizes="192x192" href="{LOGO_URL}">
        </head>
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
                            erro = str(e).lower()
                            if "confirm" in erro:
                                st.error("E-mail pendente de confirmação.")
                            else:
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

        # BUSCA DE DADOS NO SUPABASE
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

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                mes_sel = st.radio("Meses", meses, index=len(meses)-1, horizontal=True, label_visibility="collapsed")
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                rec = f[f['type'] == 'Receita']['amount'].sum()
                des = f[f['type'] == 'Despesa']['amount'].sum()
                m1, m2, m3 = st.columns(3)
                m1.metric("Receitas", f"R$ {rec:,.2f}")
                m2.metric("Despesas", f"R$ {des:,.2f}")
                m3.metric("Saldo", f"R$ {rec-des:,.2f}")
                st.markdown("---")
                col_r, col_d = st.columns(2)
                with col_r:
                    st.markdown("### 🟢 Receitas")
                    df_r = f[f['type'] == 'Receita'][['date', 'category', 'amount']].copy()
                    df_r['date'] = df_r['date'].dt.strftime('%d/%m')
                    df_r['amount'] = df_r['amount'].apply(lambda x: f"R$ {x:,.2f}")
                    st.dataframe(df_r, use_container_width=True, hide_index=True)
                with col_d:
                    st.markdown("### 🔴 Despesas")
                    df_d = f[f['type'] == 'Despesa'].copy()
                    def fmt_p(row):
                        if row['payment_method'] == "Cartão de Crédito":
                            at, tot = int(row['installment_number']), int(row['installment_total'])
                            return f"{at}/{tot}"
                        return "À vista"
                    df_d['Info'] = df_d.apply(fmt_p, axis=1)
                    df_d['amount'] = df_d['amount'].apply(lambda x: f"R$ {x:,.2f}")
                    st.dataframe(df_d[['date', 'category', 'amount', 'Info']], use_container_width=True, hide_index=True)
            else: st.info("Sem dados lançados.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                df_edit['card_name'] = df_edit['card_name'].fillna('N/A')
                df_grouped = df_edit.groupby(['category', 'card_name', 'installment_total', 'payment_method', 'type'], as_index=False, dropna=False).first()
                opcoes = {f"{r['category']} - R$ {float(r['amount'])*int(r['installment_total']):,.2f}": r['id'] for _, r in df_grouped.iterrows()}
                item_sel = st.selectbox("Selecione para editar", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                d_at = df[df['id'] == id_alvo].iloc[0]
                with st.form("edit_form"):
                    n_desc = st.text_input("Descrição", value=d_at['category'])
                    n_val_f = st.number_input("Valor Total (R$)", value=float(d_at['amount']) * int(d_at['installment_total']))
                    if st.form_submit_button("💾 ATUALIZAR TUDO"):
                        rel = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total'])]
                        v_np = n_val_f / int(d_at['installment_total'])
                        for idx, row in rel.iterrows():
                            supabase.table("profile_transactions").update({"category": n_desc, "amount": round(v_np, 2)}).eq("id", row['id']).execute()
                        st.rerun()
                    if st.form_submit_button("🗑️ EXCLUIR TUDO"):
                        rel = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total'])]
                        for _, row in rel.iterrows():
                            supabase.table("profile_transactions").delete().eq("id", row['id']).execute()
                        st.rerun()

        with tab_config:
            st.subheader("Ajustes")
            col_a, col_b = st.columns(2)
            with col_a:
                n_c = st.text_input("Novo Nome de Cartão")
                if st.button("Adicionar Cartão"):
                    if n_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                        st.rerun()
            with col_b:
                if lista_cartoes:
                    c_del = st.selectbox("Remover Cartão", lista_cartoes)
                    if st.button("Confirmar Exclusão"):
                        supabase.table("my_cards").delete().eq("id", dict_cartoes[c_del]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
