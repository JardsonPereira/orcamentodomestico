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
        # --- BUSCA DE DADOS ---
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs(["➕ Lançar", "📊 Extrato", "💳 Visão Cartão", "⚙️ Editar/Excluir", "🛠️ Ajustes"])

        # --- ABA 1: LANÇAR ---
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
                    desc = st.text_input("Descrição")
                with c2:
                    valor_total_input = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01)
                    data_origem = st.date_input("Data", datetime.now())
                    total_parc = st.number_input("Parcelas", min_value=1, step=1) if metodo_selecionado == "Cartão de Crédito" else 1

                if st.form_submit_button("Confirmar e Salvar"):
                    u_email = st.session_state.get('user_email')
                    v_parcela = valor_total_input / int(total_parc)
                    for i in range(int(total_parc)):
                        data_venc = add_months(data_origem, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parcela, 2), "date": data_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_selecionado, "card_name": cartao_vontade,
                            "installment_total": int(total_parc), "installment_number": i + 1
                        }).execute()
                    st.success("Registrado!")
                    st.rerun()

        # --- ABA 2: EXTRATO ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Filtrar Mês", sorted(df['Mês'].unique(), reverse=True))
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date')
                f['Parcela'] = f.apply(lambda x: f"{int(x['installment_number'])}/{int(x['installment_total'])}" if x['payment_method'] == "Cartão de Crédito" else "À vista", axis=1)
                
                f['Receita (R$)'] = f.apply(lambda x: float(x['amount']) if x['type'] == 'Receita' else 0.0, axis=1)
                f['Despesa (R$)'] = f.apply(lambda x: float(x['amount']) if x['type'] == 'Despesa' else 0.0, axis=1)
                f['Resultado (R$)'] = f['Receita (R$)'] - f['Despesa (R$)']
                
                t_rec = f['Receita (R$)'].sum()
                t_desp = f['Despesa (R$)'].sum()
                saldo = t_rec - t_desp

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Receitas", f"R$ {t_rec:,.2f}")
                c2.metric("Total Despesas", f"R$ {t_desp:,.2f}")
                c3.metric("Resultado Final", f"R$ {saldo:,.2f}", delta=float(saldo))

                st.markdown("---")
                exibicao = f[['date', 'category', 'Parcela', 'card_name', 'Receita (R$)', 'Despesa (R$)', 'Resultado (R$)']].copy()
                exibicao['date'] = exibicao['date'].dt.strftime('%d/%m/%Y')
                for col in ['Receita (R$)', 'Despesa (R$)', 'Resultado (R$)']:
                    exibicao[col] = exibicao[col].map('R$ {:,.2f}'.format)

                st.dataframe(exibicao.rename(columns={'date': 'Data', 'category': 'Descrição', 'card_name': 'Cartão'}), use_container_width=True, hide_index=True)

        # --- ABA 3: VISÃO CARTÃO ---
        with tab_cartao:
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    df_c['date'] = pd.to_datetime(df_c['date'])
                    hoje = datetime.now()
                    resumo = []
                    for (desc, card, total), grupo in df_c.groupby(['category', 'card_name', 'installment_total']):
                        grupo = grupo.sort_values('date')
                        proximas = grupo[grupo['date'] >= hoje.replace(day=1)]
                        parc_at = proximas.iloc[0]['installment_number'] if not proximas.empty else total
                        venc = proximas.iloc[0]['date'] if not proximas.empty else grupo.iloc[-1]['date']
                        
                        faltam = int(total) - int(parc_at)
                        resumo.append({
                            'Próximo Venc.': venc.strftime('%d/%m/%Y'),
                            'Cartão': card,
                            'Descrição': desc,
                            'Parcelas': f"{int(parc_at)}/{int(total)} (Faltam {faltam})",
                            'Valor Total Compra': f"R$ {grupo['amount'].sum():,.2f}"
                        })
                    st.dataframe(pd.DataFrame(resumo), use_container_width=True, hide_index=True)

        # --- ABA 4: GERENCIAR (COM VALOR TOTAL DA COMPRA EM CARTÃO) ---
        with tab_gerenciar:
            st.subheader("Gerenciar Lançamentos")
            if not df.empty:
                df_view = df.sort_values(by='date', ascending=False)
                opcoes = {f"{r['id']} | {pd.to_datetime(r['date']).strftime('%d/%m/%Y')} | {r['category']}": r['id'] for _, r in df_view.iterrows()}
                item_sel = st.selectbox("Selecione um lançamento:", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                
                dados_atuais = df[df['id'] == id_alvo].iloc[0]

                # Lógica para mostrar o valor total se for cartão
                if dados_atuais['payment_method'] == "Cartão de Crédito":
                    v_total_compra = float(dados_atuais['amount']) * int(dados_atuais['installment_total'])
                    st.info(f"💳 **Lançamento de Cartão:** Esta é a parcela {int(dados_atuais['installment_number'])} de {int(dados_atuais['installment_total'])}. \n\n**Valor Total da Compra Original: R$ {v_total_compra:,.2f}**")
                
                col_ed1, col_ed2 = st.columns(2)
                with col_ed1:
                    n_desc = st.text_input("Descrição", value=dados_atuais['category'])
                    n_valor = st.number_input("Valor da Parcela (R$)", value=float(dados_atuais['amount']))
                with col_ed2:
                    n_data = st.date_input("Data do Vencimento", pd.to_datetime(dados_atuais['date']))
                    st.write("")
                    c_btn1, c_btn2 = st.columns(2)
                    if c_btn1.button("💾 Salvar"):
                        supabase.table("profile_transactions").update({"category": n_desc, "amount": n_valor, "date": n_data.strftime("%Y-%m-%d")}).eq("id", id_alvo).execute()
                        st.rerun()
                    if c_btn2.button("🗑️ Excluir"):
                        supabase.table("profile_transactions").delete().eq("id", id_alvo).execute()
                        st.rerun()
            else: st.info("Sem dados para gerenciar.")

        # --- ABA 5: AJUSTES ---
        with tab_config:
            n_c = st.text_input("Novo Cartão")
            if st.button("Adicionar"):
                supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                st.rerun()

if __name__ == "__main__":
    main()
