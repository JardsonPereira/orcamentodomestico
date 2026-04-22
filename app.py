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

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- FUNÇÃO PARA PROJETAR MESES ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    st.set_page_config(page_title="Gestão Financeira Jardson", layout="wide", page_icon="💰")
    
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
            except: st.error("Erro no login.")
    else:
        st.sidebar.success(f"Conectado: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # --- BUSCA DE DADOS ---
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs(["➕ Lançar", "📊 Extrato", "💳 Visão Cartão", "⚙️ Editar/Excluir", "🛠️ Ajustes"])

        # --- ABA 1: LANÇAMENTOS (MANTIDA) ---
        with tab_lanc:
            st.subheader("Novo Lançamento")
            col_metodo, col_cartao = st.columns(2)
            with col_metodo:
                metodo_selecionado = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"], key="metodo_pag")
            
            cartao_vontade = None
            if metodo_selecionado == "Cartão de Crédito":
                with col_cartao:
                    if lista_cartoes:
                        cartao_vontade = st.selectbox("Qual Cartão?", lista_cartoes, key="card_ativo")
                    else:
                        st.warning("Cadastre um cartão na aba Ajustes.")

            with st.form("meu_formulario_lancamento", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição da Compra")
                with c2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01)
                    data_origem = st.date_input("Data da Operação", datetime.now())
                    total_parc = st.number_input("Quantidade de Parcelas", min_value=1, step=1) if metodo_selecionado == "Cartão de Crédito" else 1

                if st.form_submit_button("Confirmar e Salvar"):
                    if metodo_selecionado == "Cartão de Crédito" and not cartao_vontade:
                        st.error("Erro: Selecione um cartão!")
                    else:
                        v_parcela = valor_total / int(total_parc)
                        for i in range(int(total_parc)):
                            data_venc = add_months(data_origem, i)
                            supabase.table("profile_transactions").insert({
                                "user_email": st.session_state.user_email, "type": tipo, "category": desc,
                                "amount": round(v_parcela, 2), "date": data_venc.strftime("%Y-%m-%d"),
                                "payment_method": metodo_selecionado, "card_name": cartao_vontade,
                                "installment_total": int(total_parc), "installment_number": i + 1
                            }).execute()
                        st.success("Registrado com sucesso!")
                        st.rerun()

        # --- ABA 2: EXTRATO (COM RECEITAS E TOTAIS) ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Filtrar Mês", sorted(df['Mês'].unique(), reverse=True))
                
                f = df[df['Mês'] == mes_sel].copy()
                
                # Formatação da informação da parcela
                f['Status'] = f.apply(lambda x: f"{int(x['installment_number'])}/{int(x['installment_total'])}" if x['payment_method'] == "Cartão de Crédito" else "À vista", axis=1)
                
                # Criar colunas separadas para Receita e Despesa
                f['Receita (R$)'] = f.apply(lambda x: x['amount'] if x['type'] == 'Receita' else 0.0, axis=1)
                f['Despesa (R$)'] = f.apply(lambda x: x['amount'] if x['type'] == 'Despesa' else 0.0, axis=1)

                # Totais para os Cards
                total_receita = f['Receita (R$)'].sum()
                total_despesa = f['Despesa (R$)'].sum()
                saldo_mensal = total_receita - total_despesa

                col_r, col_d, col_s = st.columns(3)
                col_r.metric("Receitas do Mês", f"R$ {total_receita:,.2f}")
                col_d.metric("Despesas do Mês", f"R$ {total_despesa:,.2f}")
                col_s.metric("Saldo Líquido", f"R$ {saldo_mensal:,.2f}", delta=saldo_mensal)

                st.markdown("---")
                st.subheader(f"Detalhamento de {mes_sel}")
                
                # Organizar colunas para exibição
                exibicao = f[['date', 'category', 'Status', 'card_name', 'Receita (R$)', 'Despesa (R$)']].rename(
                    columns={'date': 'Vencimento', 'category': 'Descrição', 'card_name': 'Cartão'}
                )
                st.dataframe(exibicao.sort_values(by='Vencimento', ascending=False), use_container_width=True)
            else:
                st.info("Sem dados para o período.")

        # --- ABA 3: VISÃO CARTÃO ---
        with tab_cartao:
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    df_c['Faltam'] = df_c['installment_total'].astype(int) - df_c['installment_number'].astype(int)
                    df_c['Status'] = df_c.apply(lambda x: f"{int(x['installment_number'])}/{int(x['installment_total'])} (Faltam {int(x['Faltam'])})", axis=1)
                    st.dataframe(df_c[['date', 'card_name', 'category', 'Status', 'amount']].sort_values(by='date'))

        # --- ABA 4: EDITAR / EXCLUIR ---
        with tab_gerenciar:
            st.subheader("Gerenciamento de Lançamentos")
            if not df.empty:
                df_edit = df.sort_values(by='date', ascending=False)
                opcoes = {f"{r['id']} | {r['date'].strftime('%d/%m/%Y')} | {r['category']} (R$ {r['amount']:.2f})": r['id'] for _, r in df_edit.iterrows()}
                item_sel = st.selectbox("Selecione um lançamento:", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                
                dados_atuais = df[df['id'] == id_alvo].iloc[0]
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    nova_desc = st.text_input("Nova Descrição", value=dados_atuais['category'])
                    novo_valor = st.number_input("Novo Valor", value=float(dados_atuais['amount']))
                with col_e2:
                    nova_data = st.date_input("Nova Data", pd.to_datetime(dados_atuais['date']))
                    st.write("---")
                    btn_edit = st.button("💾 Salvar Alterações")
                    btn_del = st.button("🗑️ Excluir Lançamento")

                if btn_edit:
                    supabase.table("profile_transactions").update({
                        "category": nova_desc, "amount": novo_valor, "date": nova_data.strftime("%Y-%m-%d")
                    }).eq("id", id_alvo).execute()
                    st.success("Atualizado!")
                    st.rerun()
                
                if btn_del:
                    supabase.table("profile_transactions").delete().eq("id", id_alvo).execute()
                    st.warning("Excluído!")
                    st.rerun()

        # --- ABA 5: AJUSTES ---
        with tab_config:
            st.subheader("🛠️ Ajustes")
            c1, c2 = st.columns(2)
            with c1:
                n_c = st.text_input("Novo Cartão")
                if st.button("Adicionar"):
                    supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                    st.rerun()
                
                if lista_cartoes:
                    cart_del = st.selectbox("Excluir Cartão", lista_cartoes)
                    if st.button("🗑️ Remover Cartão"):
                        supabase.table("my_cards").delete().eq("card_name", cart_del).eq("user_email", st.session_state.user_email).execute()
                        st.rerun()
            with c2:
                if st.button("⚠️ Limpar Tudo"):
                    supabase.table("profile_transactions").delete().eq("user_email", st.session_state.user_email).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
