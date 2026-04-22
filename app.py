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
    st.error("Erro nas credenciais do Supabase nos Secrets.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- FUNÇÃO PARA CALCULAR MESES (PARCELAS) ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    st.set_page_config(page_title="Gestão Financeira Pro", layout="wide", page_icon="💰")
    
    if not st.session_state.logado:
        st.sidebar.title("🔐 Acesso")
        email = st.sidebar.text_input("E-mail")
        senha = st.sidebar.text_input("Senha", type='password')
        if st.sidebar.button("Entrar"):
            try:
                supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.logado = True
                st.session_state.user_email = email
                st.rerun()
            except: st.error("Login inválido")
    else:
        st.sidebar.success(f"Usuário: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        st.title("💰 Controle Financeiro Jardson")

        # Buscar dados necessários
        res_c = supabase.table("my_cards").select("card_name").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_gerenciar, tab_visao_cartao = st.tabs(["➕ Lançamentos", "📊 Extrato Mensal", "⚙️ Gerenciar Dados", "💳 Detalhe de Cartões"])

        with tab_lanc:
            with st.expander("🆕 Cadastrar Novo Cartão de Crédito"):
                nome_novo_cartao = st.text_input("Nome do Cartão")
                if st.button("Salvar Novo Cartão"):
                    if nome_novo_cartao:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": nome_novo_cartao}).execute()
                        st.success("Cartão cadastrado!")
                        st.rerun()

            st.subheader("Registrar Nova Movimentação")
            with st.form("form_financeiro", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição")
                    metodo = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
                with c2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
                    data_base = st.date_input("Data", datetime.now())
                    cartao_sel, parcelas = None, 1
                    if metodo == "Cartão de Crédito":
                        cartao_sel = st.selectbox("Selecione o Cartão", lista_cartoes)
                        parcelas = st.number_input("Parcelas", min_value=1, value=1)
                
                if st.form_submit_button("Finalizar Lançamento"):
                    valor_parc = valor_total / parcelas
                    for i in range(parcelas):
                        data_venc = add_months(data_base, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email, "type": tipo,
                            "category": f"{desc} ({i+1}/{parcelas})" if parcelas > 1 else desc,
                            "amount": valor_parc, "date": data_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo, "card_name": cartao_sel,
                            "installment_total": parcelas, "installment_number": i + 1
                        }).execute()
                    st.success("Registrado!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Mês", sorted(df['Mês'].unique(), reverse=True))
                f = df[df['Mês'] == mes_sel].copy()
                st.dataframe(f[['date', 'category', 'payment_method', 'card_name', 'amount']], use_container_width=True)
            else: st.info("Sem dados.")

        with tab_gerenciar:
            st.subheader("Editar ou Excluir Lançamentos")
            if not df.empty:
                # Seletor para escolher qual ID editar/excluir
                df_sorted = df.sort_values(by='date', ascending=False)
                opcoes_edicao = {f"{row['id']} - {row['category']} (R$ {row['amount']:.2f})": row['id'] for _, row in df_sorted.iterrows()}
                selecionado = st.selectbox("Selecione um lançamento para modificar:", list(opcoes_edicao.keys()))
                id_alvo = opcoes_edicao[selecionado]
                
                item_data = df[df['id'] == id_alvo].iloc[0]

                col_ed, col_ex = st.columns([2, 1])
                
                with col_ed:
                    st.markdown("#### Editar Campos")
                    nova_desc = st.text_input("Nova Descrição", value=item_data['category'])
                    novo_valor = st.number_input("Novo Valor", value=float(item_data['amount']))
                    if st.button("Confirmar Edição"):
                        supabase.table("profile_transactions").update({
                            "category": nova_desc, "amount": novo_valor
                        }).eq("id", id_alvo).execute()
                        st.success("Atualizado com sucesso!")
                        st.rerun()

                with col_ex:
                    st.markdown("#### Excluir")
                    st.warning("Esta ação é permanente!")
                    if st.button("🗑️ Excluir Registro"):
                        supabase.table("profile_transactions").delete().eq("id", id_alvo).execute()
                        st.error("Registro removido!")
                        st.rerun()
            else:
                st.info("Nada para gerenciar.")

        with tab_visao_cartao:
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    st.dataframe(df_c[['date', 'card_name', 'category', 'amount']], use_container_width=True)

if __name__ == "__main__":
    main()
