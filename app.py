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
    st.error("Erro: Credenciais do Supabase não configuradas nos Secrets.")
    st.stop()

st.set_page_config(page_title="Gestão Financeira", layout="wide", page_icon="💰")

# --- ESTADO DA SESSÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- FUNÇÕES DE UTILIDADE ---
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
            senha = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Aceder"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except:
                    st.error("Utilizador ou senha inválidos.")
        with aba_up:
            novo_email = st.text_input("Novo E-mail")
            nova_senha = st.text_input("Nova Senha", type="password", key="reg_pass")
            if st.button("Criar Conta"):
                try:
                    res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                    if res.user:
                        st.success("Conta criada! Pode fazer login.")
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- APP PRINCIPAL ---
if st.session_state.user is None:
    tela_login()
else:
    u_id = st.session_state.user.id
    st.sidebar.title("Menu Principal")
    menu = st.sidebar.radio("Navegação", ["Dashboard Mensal", "Novo Lançamento", "Cartões de Crédito"])
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- ABA: LANÇAMENTOS ---
    if menu == "Novo Lançamento":
        st.header("📝 Registar Movimentação")
        with st.form("form_lan"):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f", step=0.01)
            data_base = st.date_input("Data de Início", date.today())
            
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_cartoes = [c['nome_cartao'] for c in res_c.data]
            
            cartao_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/Pix/Débito"] + lista_cartoes)
            parcelas = st.number_input("Número de Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Guardar Lançamento"):
                if not desc or valor_total <= 0:
                    st.warning("Preencha os dados corretamente.")
                else:
                    dados = []
                    valor_parc = valor_total / parcelas
                    for i in range(parcelas):
                        dados.append({
                            "user_id": u_id, "tipo": tipo,
                            "descricao": f"{desc} ({i+1}/{parcelas})" if parcelas > 1 else desc,
                            "valor": round(float(valor_parc), 2),
                            "data": str(data_base + relativedelta(months=i)),
                            "parcela_atual": i + 1, "total_parcelas": parcelas,
                            "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix/Débito" else None
                        })
                    supabase.table("lancamentos").insert(dados).execute()
                    st.success("Lançamento guardado!")

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Resumo de Contas")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            mes_sel = st.selectbox("Filtrar Mês", sorted(df['MesAno'].unique(), reverse=True))
            df_mes = df[df['MesAno'] == mes_sel].copy()
            
            c1, c2, c3 = st.columns(3)
            rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            c1.metric("Receitas", format_real(rec))
            c2.metric("Despesas", format_real(des))
            c3.metric("Saldo", format_real(rec - des))
            
            st.dataframe(df_mes[['data', 'descricao', 'tipo', 'valor']], use_container_width=True)
        else:
            st.info("Sem lançamentos.")

    # --- ABA: CARTÕES ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Gestão de Cartões")
        tab_ver, tab_gerenciar, tab_add = st.tabs(["Faturas e Parcelas", "Gerenciar Cartões", "Novo Cartão"])
        
        with tab_add:
            nome_c = st.text_input("Nome do Cartão (Ex: Visa, Nubank)")
            if st.button("Registar Cartão"):
                if nome_c:
                    supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": nome_c}).execute()
                    st.success("Cartão registado!")
                    st.rerun()

        with tab_gerenciar:
            st.subheader("Eliminar Cartões")
            res_c = supabase.table("cartoes").select("*").eq("user_id", u_id).execute()
            if res_c.data:
                for cartao in res_c.data:
                    col_nome, col_btn = st.columns([3, 1])
                    col_nome.write(f"💳 **{cartao['nome_cartao']}**")
                    if col_btn.button("Eliminar", key=f"del_{cartao['id']}"):
                        # Ao deletar o cartão, os lançamentos continuam lá, mas sem o nome do cartão associado
                        supabase.table("cartoes").delete().eq("id", cartao['id']).execute()
                        st.success(f"Cartão {cartao['nome_cartao']} removido!")
                        st.rerun()
            else:
                st.write("Nenhum cartão cadastrado.")

        with tab_ver:
            res_p = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
            if res_p.data:
                df_p = pd.DataFrame(res_p.data)
                df_p['Parcelas'] = df_p['parcela_atual'].astype(str) + "/" + df_p['total_parcelas'].astype(str)
                st.table(df_p[['data', 'cartao_nome', 'descricao', 'Parcelas', 'valor']])
            else:
                st.info("Sem lançamentos de cartão.")
