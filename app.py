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
        
        /* Reset e Fontes */
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #F8F9FB; }
        
        /* Ajuste de Margens Laterais para Mobile */
        .block-container { padding: 1rem 0.8rem !important; }

        /* Estilização de Cards e Forms */
        [data-testid="stExpander"], div[data-testid="stForm"], .stContainer {
            background-color: white !important;
            border-radius: 12px !important;
            border: 1px solid #E6E9EF !important;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }

        /* Botões Estilizados */
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3.2em;
            font-weight: 600;
            background-color: #007BFF;
            color: white;
            border: none;
        }

        /* Tabelas e Dataframes */
        .stDataFrame { border-radius: 8px; overflow: hidden; }
        
        /* Responsividade das Métricas */
        @media (max-width: 640px) {
            [data-testid="stMetric"] { 
                padding: 10px !important; 
                background: white; 
                border-radius: 10px; 
                border: 1px solid #EEE;
            }
            .stTabs [data-baseweb="tab-list"] { gap: 2px; }
            .stTabs [data-baseweb="tab"] { padding: 5px 8px; font-size: 11px; }
        }
        </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.logado:
        # --- TELA DE ACESSO ---
        st.markdown("<h1 style='text-align: center; color: #1E293B;'>💰 ContabilApp</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([0.1, 0.8, 0.1])
        with col_central:
            escolha = st.radio("Ação", ["Entrar", "Criar Conta"], horizontal=True, label_visibility="collapsed")
            
            with st.container():
                if escolha == "Entrar":
                    st.subheader("Login")
                    email = st.text_input("E-mail")
                    senha = st.text_input("Senha", type='password')
                    nome_login = st.text_input("Seu Nome")
                    
                    if st.button("ACESSAR"):
                        try:
                            supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            st.session_state.logado = True
                            st.session_state.user_email = email
                            st.session_state.user_name = nome_login
                            st.rerun()
                        except: st.error("Erro no login. Verifique os dados.")
                            
                else:
                    st.subheader("Cadastro rápido")
                    novo_nome = st.text_input("Nome")
                    novo_email = st.text_input("E-mail")
                    nova_senha = st.text_input("Senha", type='password')
                    
                    if st.button("FINALIZAR CADASTRO"):
                        try:
                            supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                            st.session_state.logado = True
                            st.session_state.user_email = novo_email
                            st.session_state.user_name = novo_nome
                            st.success("Conta criada!")
                            st.rerun()
                        except: st.error("Erro ao criar conta.")

    else:
        # --- APP PRINCIPAL ---
        header_col, logout_col = st.columns([4, 1])
        header_col.markdown(f"### Olá, **{st.session_state.get('user_name', 'Usuário')}** 👋")
        if logout_col.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # Busca de Dados
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        # Abas Mobile (Ícones para economizar espaço)
        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs([
            "➕ Lançar", "📊 Extrato", "💳 Cartões", "⚙️ Editar", "🛠️ Ajustes"
        ])

        with tab_lanc:
            st.subheader("Nova Transação")
            metodo = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
            
            cart_sel = None
            if metodo == "Cartão de Crédito":
                if lista_cartoes:
                    cart_sel = st.selectbox("Qual cartão?", lista_cartoes)
                else:
                    st.warning("Cadastre um cartão na última aba.")

            with st.form("form_novo", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                desc = st.text_input("Descrição")
                valor = st.number_input("Valor Total (R$)", min_value=0.0, step=0.01)
                data_in = st.date_input("Data", datetime.now())
                
                parc = 1
                if metodo == "Cartão de Crédito":
                    parc = st.number_input("Nº de Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 SALVAR"):
                    u_email = st.session_state.user_email
                    v_parc = valor / int(parc)
                    for i in range(int(parc)):
                        d_venc = add_months(data_in, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parc, 2), "date": d_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo, "card_name": cart_sel,
                            "installment_total": int(parc), "installment_number": i + 1
                        }).execute()
                    st.success("Lançado!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                
                mes_sel = st.selectbox("Filtrar Mês", meses, index=len(meses)-1)
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                
                # Resumo financeiro
                c1, c2 = st.columns(2)
                rec = f[f['type'] == 'Receita']['amount'].sum()
                des = f[f['type'] == 'Despesa']['amount'].sum()
                c1.metric("Ganhos", f"R$ {rec:,.2f}")
                c2.metric("Gastos", f"R$ {des:,.2f}", delta=f"-{des:,.2f}", delta_color="inverse")
                st.metric("Saldo Líquido", f"R$ {rec-des:,.2f}")

                st.markdown("---")
                # Tabela organizada por Entradas/Saídas
                col_e, col_s = st.columns(2)
                with col_e:
                    st.caption("🟢 Entradas")
                    st.dataframe(f[f['type'] == 'Receita'][['date', 'category', 'amount']], use_container_width=True, hide_index=True)
                with col_s:
                    st.caption("🔴 Saídas")
                    st.dataframe(f[f['type'] == 'Despesa'][['date', 'category', 'amount']], use_container_width=True, hide_index=True)
            else: st.info("Sem lançamentos ainda.")

        with tab_cartao:
            if not df.empty and lista_cartoes:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                df_c['date'] = pd.to_datetime(df_c['date'])
                for cartao in lista_cartoes:
                    with st.container():
                        st.markdown(f"#### 💳 {cartao}")
                        dados = df_c[df_c['card_name'] == cartao]
                        if not dados.empty:
                            mes_fatura = dados[dados['date'].dt.month == datetime.now().month]
                            st.metric("Fatura Aberta", f"R$ {mes_fatura['amount'].sum():,.2f}")
                        else: st.caption("Sem gastos registrados.")
            else: st.info("Nenhum cartão cadastrado.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                # Agrupamento para edição total
                df_grouped = df_edit.sort_values(['category', 'installment_total', 'date'])
                df_grouped = df_grouped.groupby(['category', 'installment_total', 'type', 'payment_method'], as_index=False).first()
                
                opcoes = {f"{r['category']} | {r['payment_method']} (Total: R${float(r['amount'])*int(r['installment_total']):.2f})": r['id'] for _, r in df_grouped.iterrows()}
                item_sel = st.selectbox("O que deseja alterar?", list(opcoes.keys()))
                
                d_at = df[df['id'] == opcoes[item_sel]].iloc[0]
                with st.form("edit_form_total"):
                    st.write(f"Editando compra em: **{d_at['payment_method']}**")
                    n_desc = st.text_input("Novo Nome", value=d_at['category'])
                    n_valor_total = st.number_input("Novo Valor Total", value=float(d_at['amount']) * int(d_at['installment_total']))
                    
                    if st.form_submit_button("ATUALIZAR COMPRA COMPLETA"):
                        # Atualiza todas as parcelas de uma vez
                        valor_p = n_valor_total / int(d_at['installment_total'])
                        supabase.table("profile_transactions").update({
                            "category": n_desc, 
                            "amount": round(valor_p, 2)
                        }).eq("category", d_at['category']).eq("installment_total", d_at['installment_total']).execute()
                        st.success("Alterado em todas as parcelas!")
                        st.rerun()
                    
                    if st.form_submit_button("🗑️ EXCLUIR TUDO"):
                        supabase.table("profile_transactions").delete().eq("category", d_at['category']).eq("installment_total", d_at['installment_total']).execute()
                        st.rerun()

        with tab_config:
            st.subheader("Configurações")
            c1, c2 = st.columns(2)
            with c1:
                n_cartao = st.text_input("Novo Cartão")
                if st.button("ADICIONAR CARTÃO"):
                    if n_cartao:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_cartao}).execute()
                        st.rerun()
            with c2:
                if lista_cartoes:
                    del_c = st.selectbox("Remover Cartão", lista_cartoes)
                    if st.button("EXCLUIR CARTÃO"):
                        supabase.table("my_cards").delete().eq("id", dict_cartoes[del_c]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
