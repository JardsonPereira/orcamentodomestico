import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Erro: Credenciais do Supabase não encontradas.")
    st.stop()

st.set_page_config(page_title="Gestão Financeira", layout="wide", page_icon="💰")

# --- ESTADO DA SESSÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

def format_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

# --- AUTENTICAÇÃO ---
def tela_login():
    st.title("💰 Orçamento Doméstico")
    col_l, _ = st.columns([1, 1])
    with col_l:
        aba_in, aba_up = st.tabs(["Entrar", "Cadastrar"])
        with aba_in:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Aceder"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except:
                    st.error("Login inválido.")
        with aba_up:
            n_email = st.text_input("Novo E-mail")
            n_senha = st.text_input("Nova Senha", type="password")
            if st.button("Criar Conta"):
                try:
                    supabase.auth.sign_up({"email": n_email, "password": n_senha})
                    st.success("Conta criada! Tente logar.")
                except Exception as e:
                    st.error(f"Erro: {e}")

if st.session_state.user is None:
    tela_login()
else:
    u_id = st.session_state.user.id
    st.sidebar.title("Menu")
    menu = st.sidebar.radio("Navegação", ["Dashboard Mensal", "Novo Lançamento", "Cartões de Crédito"])
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- NOVO LANÇAMENTO ---
    if menu == "Novo Lançamento":
        st.header("📝 Novo Lançamento")
        with st.form("form_lan"):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
            dt_base = st.date_input("Data", date.today())
            
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_c = [c['nome_cartao'] for c in res_c.data]
            cartao_sel = st.selectbox("Cartão", ["Dinheiro/Pix"] + lista_c)
            parcelas = st.number_input("Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Salvar"):
                v_parc = valor_total / parcelas
                dados = []
                for i in range(parcelas):
                    dados.append({
                        "user_id": u_id, "tipo": tipo, "descricao": desc,
                        "valor": round(float(v_parc), 2),
                        "data": str(dt_base + relativedelta(months=i)),
                        "parcela_atual": i + 1, "total_parcelas": parcelas,
                        "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix" else None
                    })
                supabase.table("lancamentos").insert(dados).execute()
                st.success("Salvo!")

    # --- DASHBOARD ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Dashboard")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['Mes'] = df['data'].dt.strftime('%m/%Y')
            mes_sel = st.selectbox("Mês", sorted(df['Mes'].unique(), reverse=True))
            df_mes = df[df['Mes'] == mes_sel]
            
            c1, c2 = st.columns(2)
            c1.metric("Receitas", format_real(df_mes[df_mes['tipo']=='Receita']['valor'].sum()))
            c2.metric("Despesas", format_real(df_mes[df_mes['tipo']=='Despesa']['valor'].sum()))
            st.dataframe(df_mes[['data', 'descricao', 'valor']], use_container_width=True)

    # --- CARTÕES (COM AGRUPAMENTO SOLICITADO) ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Cartões de Crédito")
        tab1, tab2, tab3 = st.tabs(["Resumo de Compras", "Gerenciar Cartões", "Novo Cartão"])

        with tab3:
            n_c = st.text_input("Nome do Cartão")
            if st.button("Salvar Cartão"):
                supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": n_c}).execute()
                st.rerun()

        with tab2:
            res_c = supabase.table("cartoes").select("*").eq("user_id", u_id).execute()
            for c in res_c.data:
                col_n, col_b = st.columns([3, 1])
                col_n.write(f"💳 {c['nome_cartao']}")
                if col_b.button("Excluir", key=c['id']):
                    supabase.table("cartoes").delete().eq("id", c['id']).execute()
                    st.rerun()

        with tab1:
            res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
            if res_l.data:
                df_p = pd.DataFrame(res_l.data)
                
                # LÓGICA DE AGRUPAMENTO:
                # Agrupamos por Descrição e Cartão para mostrar apenas uma linha por compra
                hoje = pd.to_datetime(date.today())
                
                # Calculamos o total da compra e qual a parcela atual (baseado na data de hoje)
                resumo = df_p.groupby(['descricao', 'cartao_nome', 'total_parcelas']).agg({
                    'valor': 'sum',
                    'data': 'min'
                }).reset_index()

                # Para saber a "parcela paga", contamos quantos lançamentos daquela compra têm data <= hoje
                df_p['data'] = pd.to_datetime(df_p['data'])
                pagas = df_p[df_p['data'] <= hoje].groupby(['descricao', 'cartao_nome']).size().reset_index(name='pagas')
                
                resumo = pd.merge(resumo, pagas, on=['descricao', 'cartao_nome'], how='left').fillna(0)
                resumo['pagas'] = resumo['pagas'].astype(int)
                
                # Formatação solicitada: total_parcelas/pagas (Ex: 10/1)
                resumo['Parcelas'] = resumo['total_parcelas'].astype(str) + "/" + resumo['pagas'].astype(str)
                resumo['Valor Total'] = resumo['valor'].apply(format_real)
                
                st.table(resumo[['cartao_nome', 'descricao', 'Parcelas', 'Valor Total']])
            else:
                st.info("Sem compras parceladas.")
