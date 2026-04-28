import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO SUPABASE ---
# No Streamlit Cloud, configure em: Settings > Secrets
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
    """Formata um número para o padrão brasileiro: R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

# --- AUTENTICAÇÃO ---
def tela_login():
    st.title("💰 Orçamento Doméstico")
    col_l, col_r = st.columns([1, 1])
    
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
                    # Nota: Certifique-se de que "Confirm Email" está OFF no Supabase
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
    st.sidebar.write(f"Logado como: \n**{st.session_state.user.email}**")
    
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
            desc = st.text_input("Descrição (Ex: Salário, Aluguer, Compras)")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f", step=0.01)
            data_base = st.date_input("Data de Início", date.today())
            
            # Buscar cartões do utilizador
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_cartoes = [c['nome_cartao'] for c in res_c.data]
            
            cartao_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/Pix/Débito"] + lista_cartoes)
            parcelas = st.number_input("Número de Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Guardar Lançamento"):
                if not desc or valor_total <= 0:
                    st.warning("Preencha a descrição e o valor.")
                else:
                    dados = []
                    valor_parc = valor_total / parcelas
                    for i in range(parcelas):
                        dados.append({
                            "user_id": u_id,
                            "tipo": tipo,
                            "descricao": f"{desc} ({i+1}/{parcelas})" if parcelas > 1 else desc,
                            "valor": round(float(valor_parc), 2),
                            "data": str(data_base + relativedelta(months=i)),
                            "parcela_atual": i + 1,
                            "total_parcelas": parcelas,
                            "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix/Débito" else None
                        })
                    
                    try:
                        supabase.table("lancamentos").insert(dados).execute()
                        st.success(f"Lançamento de {parcelas}x guardado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Resumo de Contas")
        
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            
            meses_disp = sorted(df['MesAno'].unique(), reverse=True)
            mes_sel = st.selectbox("Filtrar Mês", meses_disp)
            
            df_mes = df[df['MesAno'] == mes_sel].copy()
            
            # Resumo Financeiro
            receitas = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            despesas = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            saldo = receitas - despesas
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Receitas", format_real(receitas))
            c2.metric("Despesas", format_real(despesas))
            c3.metric("Saldo", format_real(saldo), delta=format_real(saldo))
            
            st.divider()
            st.subheader(f"Lista de Lançamentos - {mes_sel}")
            
            df_view = df_mes.sort_values(by='data')
            df_view['Valor'] = df_view['valor'].apply(format_real)
            df_view['Data'] = df_view['data'].dt.strftime('%d/%m/%Y')
            
            st.dataframe(df_view[['Data', 'descricao', 'tipo', 'Valor']], use_container_width=True)
        else:
            st.info("Ainda não tem lançamentos registados.")

    # --- ABA: CARTÕES ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Gestão de Cartões")
        
        tab_ver, tab_add = st.tabs(["Meus Cartões e Parcelas", "Novo Cartão"])
        
        with tab_add:
            nome_c = st.text_input("Nome do Cartão (Ex: Visa, Nubank)")
            if st.button("Registar Cartão"):
                if nome_c:
                    try:
                        supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": nome_c}).execute()
                        st.success("Cartão registado!")
                        st.rerun()
                    except Exception as e:
                        st.error("Erro: Tente novamente. Verifique se o RLS está ativo no Supabase.")

        with tab_ver:
            res_p = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
            if res_p.data:
                df_p = pd.DataFrame(res_p.data)
                df_p['Parcelas'] = df_p['parcela_atual'].astype(str) + "/" + df_p['total_parcelas'].astype(str)
                df_p['Valor Parcela'] = df_p['valor'].apply(format_real)
                
                cartao_filtro = st.selectbox("Filtrar Cartão", ["Todos"] + list(df_p['cartao_nome'].unique()))
                if cartao_filtro != "Todos":
                    df_p = df_p[df_p['cartao_nome'] == cartao_filtro]
                
                st.table(df_p[['data', 'cartao_nome', 'descricao', 'Parcelas', 'Valor Parcela']])
            else:
                st.info("Sem lançamentos de cartão de crédito.")
