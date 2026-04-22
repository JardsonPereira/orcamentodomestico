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
    # --- UI MODERNA ---
    st.set_page_config(page_title="ContabilApp Pro", layout="wide", page_icon="💰")
    
    # CSS Customizado para um visual mais limpo
    st.markdown("""
        <style>
        .main { background-color: #f5f7f9; }
        .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        div[data-testid="stExpander"] { border: none !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; background: white; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.logado:
        st.sidebar.title("🔐 Acesso Restrito")
        email = st.sidebar.text_input("E-mail")
        senha = st.sidebar.text_input("Senha", type='password')
        if st.sidebar.button("Entrar no Sistema"):
            try:
                supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.logado = True
                st.session_state.user_email = email
                st.rerun()
            except: st.error("E-mail ou senha incorretos.")
    else:
        # --- HEADER ---
        c_head1, c_head2 = st.columns([4, 1])
        c_head1.title("💰 Gestão Financeira Inteligente")
        c_head2.write(f"👤 {st.session_state.user_email}")
        if c_head2.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # --- BUSCA DE DADOS ---
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        # --- ABAS MODERNAS ---
        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs([
            "➕ Lançamentos", "📊 Dash & Extrato", "💳 Faturas", "⚙️ Manutenção", "🛠️ Ajustes"
        ])

        with tab_lanc:
            with st.container():
                st.subheader("Registrar Movimentação")
                col_metodo, col_cartao = st.columns(2)
                with col_metodo:
                    metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"], key="metodo_pag")
                
                cart_vontade = None
                if metodo_sel == "Cartão de Crédito":
                    with col_cartao:
                        if lista_cartoes:
                            cart_vontade = st.selectbox("Qual Cartão?", lista_cartoes, key="card_ativo")
                        else:
                            st.warning("Cadastre um cartão na aba Ajustes.")

                with st.expander("📝 Detalhes da Transação", expanded=True):
                    with st.form("form_v3", clear_on_submit=True):
                        c1, c2 = st.columns(2)
                        with c1:
                            tipo = st.selectbox("Categoria de Fluxo", ["Despesa", "Receita"])
                            desc = st.text_input("Descrição (Ex: Aluguel, Supermercado)")
                        with c2:
                            valor_total = st.number_input("Valor (R$)", min_value=0.01, step=0.01)
                            data_origem = st.date_input("Data", datetime.now())
                            total_parc = st.number_input("Parcelas", min_value=1, step=1) if metodo_sel == "Cartão de Crédito" else 1

                        if st.form_submit_button("Confirmar Lançamento"):
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
                            st.success("✅ Registro realizado com sucesso!")
                            st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Selecione o Período", sorted(df['Mês'].unique(), reverse=True))
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date')
                f['Parcela'] = f.apply(lambda x: f"{int(x['installment_number'])}/{int(x['installment_total'])}" if x['payment_method'] == "Cartão de Crédito" else "À vista", axis=1)
                
                f['Receita (R$)'] = f.apply(lambda x: float(x['amount']) if x['type'] == 'Receita' else 0.0, axis=1)
                f['Despesa (R$)'] = f.apply(lambda x: float(x['amount']) if x['type'] == 'Despesa' else 0.0, axis=1)
                
                # --- CARDS DE MÉTRICAS ---
                t_rec, t_desp = f['Receita (R$)'].sum(), f['Despesa (R$)'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("📈 Total Receitas", f"R$ {t_rec:,.2f}")
                c2.metric("📉 Total Despesas", f"R$ {t_desp:,.2f}")
                c3.metric("⚖️ Saldo do Mês", f"R$ {t_rec - t_desp:,.2f}", delta=float(t_rec - t_desp))

                st.markdown("### 📋 Extrato Detalhado")
                exibicao = f[['date', 'category', 'Parcela', 'card_name', 'Receita (R$)', 'Despesa (R$)']].copy()
                exibicao['date'] = exibicao['date'].dt.strftime('%d/%m/%Y')
                for col in ['Receita (R$)', 'Despesa (R$)']:
                    exibicao[col] = exibicao[col].map('R$ {:,.2f}'.format)

                st.dataframe(exibicao.rename(columns={'date': 'Data', 'category': 'Item', 'card_name': 'Origem'}), use_container_width=True, hide_index=True)
            else: st.info("ℹ️ Comece adicionando o seu primeiro lançamento.")

        with tab_cartao:
            st.subheader("💳 Projeção de Faturas")
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
                        resumo.append({
                            'Próximo Venc.': venc.strftime('%d/%m/%Y'),
                            'Cartão': card, 'Item': desc,
                            'Progresso': f"{int(parc_at)}/{int(total)} (Faltam {int(total)-int(parc_at)})",
                            'Total Compra': f"R$ {grupo['amount'].sum():,.2f}"
                        })
                    st.dataframe(pd.DataFrame(resumo), use_container_width=True, hide_index=True)

        with tab_gerenciar:
            st.subheader("⚙️ Manutenção de Dados")
            if not df.empty:
                df_view = df.sort_values(by='date', ascending=False)
                opcoes = {f"{r['id']} | {pd.to_datetime(r['date']).strftime('%d/%m/%Y')} | {r['category']}": r['id'] for _, r in df_view.iterrows()}
                item_sel = st.selectbox("Selecione o registro para editar ou remover:", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                d_at = df[df['id'] == id_alvo].iloc[0]

                if d_at['payment_method'] == "Cartão de Crédito":
                    st.info(f"💡 Dica: Este item é a parcela {int(d_at['installment_number'])} de {int(d_at['installment_total'])}.")
                
                with st.form("edit_form"):
                    col_e1, col_e2 = st.columns(2)
                    n_desc = col_e1.text_input("Nova Descrição", value=d_at['category'])
                    n_valor = col_e1.number_input("Novo Valor (R$)", value=float(d_at['amount']))
                    n_data = col_e2.date_input("Nova Data", pd.to_datetime(d_at['date']))
                    
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.form_submit_button("💾 Salvar"):
                        supabase.table("profile_transactions").update({"category": n_desc, "amount": n_valor, "date": n_data.strftime("%Y-%m-%d")}).eq("id", id_alvo).execute()
                        st.rerun()
                    if c_b2.form_submit_button("🗑️ Excluir"):
                        supabase.table("profile_transactions").delete().eq("id", id_alvo).execute()
                        st.rerun()

        with tab_config:
            st.subheader("🛠️ Painel de Controle")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Gerenciar Cartões**")
                n_c = st.text_input("Nome do Cartão", placeholder="Ex: Inter Platinum")
                if st.button("Adicionar"):
                    if n_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                        st.rerun()
                
                if lista_cartoes:
                    cart_del = st.selectbox("Remover Cartão", lista_cartoes)
                    if st.button("Confirmar Remoção"):
                        supabase.table("my_cards").delete().eq("id", dict_cartoes[cart_del]).execute()
                        st.rerun()

            with col_b:
                st.write("**Banco de Dados**")
                st.warning("Cuidado! As ações abaixo não podem ser desfeitas.")
                if st.button("🧨 Resetar Todos os Lançamentos"):
                    supabase.table("profile_transactions").delete().eq("user_email", st.session_state.user_email).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
