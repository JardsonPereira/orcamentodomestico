import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais. Verifique os Secrets.")
    st.stop()

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    # --- CONFIGURAÇÃO VISUAL MOBILE-FIRST ---
    st.set_page_config(page_title="ContabilApp Pro", layout="wide", page_icon="💰")
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        /* Ajustes Gerais Celular */
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #F0F2F5; }
        
        /* Ajuste de Margens Laterais para Mobile */
        .block-container { padding: 1rem 1rem !important; }

        @media (max-width: 640px) {
            h1 { font-size: 1.5rem !important; }
            .stMetric { padding: 10px !important; }
            [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
            .stTabs [data-baseweb="tab-list"] { gap: 5px; }
            .stTabs [data-baseweb="tab"] { padding: 8px 10px; font-size: 12px; }
        }

        /* Estilização de Botões e Cards */
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3.5em;
            font-weight: 600;
        }
        
        [data-testid="stExpander"], div[data-testid="stForm"], div.stContainer {
            background-color: white !important;
            border-radius: 15px !important;
            border: 1px solid #E0E0E0 !important;
            margin-bottom: 10px;
        }

        /* Melhora a visualização de tabelas no celular */
        .stDataFrame { width: 100% !important; }
        </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.logado:
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        col_login = st.columns([1])[0] # Coluna única no mobile
        
        with col_login:
            escolha = st.radio("Opção:", ["Entrar na Conta", "Criar Nova Conta"], horizontal=True, label_visibility="collapsed")
            
            with st.container(border=True):
                if escolha == "Entrar na Conta":
                    st.subheader("Login")
                    email = st.text_input("E-mail")
                    senha = st.text_input("Senha", type='password')
                    nome_fantasia = st.text_input("Seu Nome")
                    
                    if st.button("ACESSAR"):
                        try:
                            supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            st.session_state.logado = True
                            st.session_state.user_email = email
                            st.session_state.user_name = nome_fantasia
                            st.rerun()
                        except:
                            st.error("Erro no login.")
                            
                else:
                    st.subheader("Cadastro")
                    novo_nome = st.text_input("Nome")
                    novo_email = st.text_input("E-mail")
                    nova_senha = st.text_input("Senha (mín. 6 car.)", type='password')
                    
                    if st.button("CRIAR CONTA"):
                        try:
                            supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                            st.session_state.logado = True
                            st.session_state.user_email = novo_email
                            st.session_state.user_name = novo_nome
                            st.success("Conta criada!")
                            st.rerun()
                        except Exception as e:
                            st.error("Erro no cadastro.")

    else:
        # HEADER COMPACTO
        col_title, col_user = st.columns([2, 1])
        with col_title:
            st.markdown(f"### Olá, {st.session_state.get('user_name', 'Usuário')}")
        with col_user:
            if st.button("Sair", key="logout_btn"):
                st.session_state.logado = False
                st.rerun()

        # DADOS
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs([
            "➕", "📊", "💳", "⚙️", "🛠️"
        ])

        with tab_lanc:
            st.subheader("Novo Lançamento")
            metodo_sel = st.selectbox("Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
            
            cart_vontade = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes:
                    cart_vontade = st.selectbox("Qual Cartão?", lista_cartoes)
                else:
                    st.warning("Cadastre um cartão.")

            with st.form("form_mobile", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                desc = st.text_input("O que é?")
                valor_total = st.number_input("Valor (R$)", min_value=0.01, step=0.10)
                data_origem = st.date_input("Quando?", datetime.now())
                
                total_parc = 1
                if metodo_sel == "Cartão de Crédito":
                    total_parc = st.number_input("Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 SALVAR"):
                    u_email = st.session_state.get('user_email')
                    v_parc = valor_total / int(total_parc)
                    for i in range(int(total_parc)):
                        data_venc = add_months(data_origem, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parc, 2), "date": data_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_sel, "card_name": cart_vontade,
                            "installment_total": int(total_parc), "installment_number": i + 1
                        }).execute()
                    st.success("Salvo!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                
                mes_sel = st.selectbox("Mês:", meses, index=len(meses)-1)
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                
                # Métricas Empilhadas no Mobile
                rec_total = f[f['type'] == 'Receita']['amount'].sum()
                des_total = f[f['type'] == 'Despesa']['amount'].sum()
                
                st.metric("Receitas", f"R$ {rec_total:,.2f}")
                st.metric("Despesas", f"R$ {des_total:,.2f}")
                st.metric("Saldo", f"R$ {rec_total-des_total:,.2f}")

                st.markdown("---")
                # Tabela com uso total da largura
                st.dataframe(f[['date', 'category', 'amount']], use_container_width=True, hide_index=True)
            else: st.info("Sem dados.")

        with tab_cartao:
            if not df.empty and lista_cartoes:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                df_c['date'] = pd.to_datetime(df_c['date'])
                for nome_cartao in lista_cartoes:
                    with st.container(border=True):
                        st.write(f"**{nome_cartao}**")
                        dados = df_c[df_c['card_name'] == nome_cartao]
                        if not dados.empty:
                            total = dados[dados['date'].dt.month == datetime.now().month]['amount'].sum()
                            st.write(f"Fatura: R$ {total:,.2f}")
            else: st.info("Sem cartões.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                df_grouped = df_edit.groupby(['category', 'installment_total', 'type'], as_index=False).first()
                
                opcoes = {f"{r['category']} (R${float(r['amount'])*int(r['installment_total']):.2f})": r['id'] for _, r in df_grouped.iterrows()}
                item_sel = st.selectbox("Editar:", list(opcoes.keys()))
                
                d_at = df[df['id'] == opcoes[item_sel]].iloc[0]
                with st.form("edit_form"):
                    n_desc = st.text_input("Nome", value=d_at['category'])
                    n_val = st.number_input("Valor Total", value=float(d_at['amount']) * int(d_at['installment_total']))
                    if st.form_submit_button("ATUALIZAR"):
                        supabase.table("profile_transactions").update({"category": n_desc, "amount": n_val/int(d_at['installment_total'])}).eq("category", d_at['category']).execute()
                        st.rerun()

        with tab_config:
            st.subheader("Ajustes")
            n_c = st.text_input("Novo Cartão")
            if st.button("Adicionar"):
                supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                st.rerun()
            if lista_cartoes:
                cart_del = st.selectbox("Excluir Cartão", lista_cartoes)
                if st.button("Excluir"):
                    supabase.table("my_cards").delete().eq("id", dict_cartoes[cart_del]).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
