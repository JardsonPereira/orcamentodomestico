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
    # --- CONFIGURAÇÃO VISUAL ---
    st.set_page_config(page_title="ContabilApp Pro", layout="wide", page_icon="💰")
    
    # CSS AVANÇADO PARA UI/UX
    st.markdown("""
        <style>
        /* Importando fonte moderna */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }

        /* Fundo do App */
        .stApp {
            background-color: #F0F2F5;
        }

        /* Estilização das Métricas */
        [data-testid="stMetric"] {
            background-color: white;
            padding: 15px !important;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid #E0E0E0;
        }

        /* Botões */
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3.5em;
            background-color: #2E6FF2;
            color: white;
            font-weight: 600;
            border: none;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #1A54C5;
            box-shadow: 0 4px 12px rgba(46, 111, 242, 0.3);
        }

        /* Tabs (Abas) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: white;
            border-radius: 8px;
            padding: 0 20px;
            border: 1px solid #E0E0E0;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #2E6FF2;
        }

        /* Containers e Cards */
        [data-testid="stExpander"], div[data-testid="stForm"] {
            background-color: white !important;
            border-radius: 15px !important;
            border: 1px solid #E0E0E0 !important;
            padding: 10px;
        }

        /* Títulos */
        h1, h2, h3 {
            color: #1A1A1A;
            font-weight: 700 !important;
        }

        /* Estilo para Radio Horizontal (Meses) */
        div[data-testid="stHorizontalBlock"] {
            background: white;
            padding: 10px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
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
            except: st.sidebar.error("Dados incorretos.")
    else:
        # HEADER
        col_title, col_user = st.columns([3, 1])
        with col_title:
            st.title("💰 Minhas Finanças")
        with col_user:
            with st.expander(f"👤 Perfil"):
                st.write(st.session_state.user_email)
                if st.button("Sair"):
                    st.session_state.logado = False
                    st.rerun()

        # DADOS
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs([
            "➕ Lançar", "📊 Extrato", "💳 Cartões", "⚙️ Editar", "🛠️ Ajustes"
        ])

        with tab_lanc:
            st.subheader("Registrar Movimentação")
            metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"], key="metodo_pag")
            
            cart_vontade = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes:
                    cart_vontade = st.selectbox("Selecione o Cartão", lista_cartoes, key="card_ativo")
                else:
                    st.warning("Cadastre um cartão primeiro.")

            with st.form("form_mobile", clear_on_submit=True):
                col1, col2 = st.columns(2)
                tipo = col1.selectbox("Tipo", ["Despesa", "Receita"])
                desc = col2.text_input("Descrição (ex: Aluguel, Supermercado)")
                
                col3, col4 = st.columns(2)
                valor_total = col3.number_input("Valor Total (R$)", min_value=0.01, step=0.10)
                data_origem = col4.date_input("Data", datetime.now())
                
                total_parc = 1
                if metodo_sel == "Cartão de Crédito":
                    total_parc = st.number_input("Número de Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 SALVAR LANÇAMENTO"):
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
                    st.success("✅ Lançamento realizado!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses_disponiveis = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                mes_atual_str = datetime.now().strftime('%m/%Y')
                try: default_idx = meses_disponiveis.index(mes_atual_str)
                except: default_idx = len(meses_disponiveis) - 1

                st.write("**Selecione o Mês:**")
                mes_sel = st.radio("Meses", meses_disponiveis, index=default_idx, horizontal=True, label_visibility="collapsed")
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                
                m1, m2, m3 = st.columns(3)
                rec_total = f[f['type'] == 'Receita']['amount'].sum()
                des_total = f[f['type'] == 'Despesa']['amount'].sum()
                m1.metric("Receitas", f"R$ {rec_total:,.2f}", delta_color="normal")
                m2.metric("Despesas", f"R$ {des_total:,.2f}", delta="-", delta_color="inverse")
                m3.metric("Saldo", f"R$ {rec_total-des_total:,.2f}")

                st.markdown("---")
                col_rec, col_des = st.columns(2)
                
                with col_rec:
                    st.markdown("### 🟢 Entradas")
                    df_rec = f[f['type'] == 'Receita'][['date', 'category', 'amount']].copy()
                    if not df_rec.empty:
                        df_rec['date'] = df_rec['date'].dt.strftime('%d/%m')
                        st.dataframe(df_rec, use_container_width=True, hide_index=True)
                    else: st.info("Sem entradas.")

                with col_des:
                    st.markdown("### 🔴 Saídas")
                    df_des = f[f['type'] == 'Despesa'][['date', 'category', 'amount']].copy()
                    if not df_des.empty:
                        df_des['date'] = df_des['date'].dt.strftime('%d/%m')
                        st.dataframe(df_des, use_container_width=True, hide_index=True)
                    else: st.info("Sem saídas.")
            else: st.info("Nenhum dado encontrado.")

        with tab_cartao:
            if not df.empty and lista_cartoes:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                df_c['date'] = pd.to_datetime(df_c['date'])
                hoje = datetime.now()
                
                for nome_cartao in lista_cartoes:
                    with st.container():
                        st.markdown(f"""
                            <div style="background-color: white; padding: 20px; border-radius: 15px; border-left: 5px solid #2E6FF2; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                                <h3 style="margin:0;">💳 {nome_cartao}</h3>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        dados_este_cartao = df_c[df_c['card_name'] == nome_cartao]
                        if not dados_este_cartao.empty:
                            total_fatura = dados_este_cartao[dados_este_cartao['date'].dt.strftime('%m/%Y') == hoje.strftime('%m/%Y')]['amount'].sum()
                            c1, c2 = st.columns([1, 2])
                            c1.metric("Fatura Atual", f"R$ {total_fatura:,.2f}")
                            
                            resumo_cartao = []
                            for (desc, total), grupo in dados_este_cartao.groupby(['category', 'installment_total']):
                                grupo = grupo.sort_values('date')
                                proximas = grupo[grupo['date'] >= hoje.replace(day=1)]
                                if not proximas.empty:
                                    parc_at = proximas.iloc[0]['installment_number']
                                    venc = proximas.iloc[0]['date']
                                    resumo_cartao.append({
                                        'Vencimento': venc.strftime('%d/%m'),
                                        'Descrição': desc,
                                        'Parcela': f"{int(parc_at)}/{int(total)}",
                                        'Valor Parcela': f"R$ {proximas.iloc[0]['amount']:,.2f}"
                                    })
                            if resumo_cartao:
                                with c2: st.table(pd.DataFrame(resumo_cartao))
                        else: st.caption("Sem gastos neste cartão.")
            else: st.info("Cadastre cartões para ver o resumo.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                df_edit['card_name'] = df_edit['card_name'].fillna('N/A')
                
                df_grouped = df_edit.sort_values(['category', 'card_name', 'installment_total', 'date'])
                df_grouped = df_grouped.groupby(['category', 'card_name', 'installment_total', 'payment_method', 'type'], as_index=False, dropna=False).first()
                df_grouped = df_grouped.sort_values(by='date', ascending=False)
                
                opcoes = {}
                for _, r in df_grouped.iterrows():
                    v_total = float(r['amount']) * int(r['installment_total'])
                    prefixo = "💰" if r['type'] == 'Receita' else ("💳" if r['payment_method'] == "Cartão de Crédito" else "💵")
                    parc_txt = f" [{int(r['installment_total'])}x]" if r['payment_method'] == "Cartão de Crédito" else ""
                    label = f"{prefixo} {r['date'].strftime('%d/%m/%y')} | {r['category']}{parc_txt} - R${v_total:,.2f}"
                    opcoes[label] = r['id']
                
                item_sel = st.selectbox("Selecione o registro para editar", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                d_at = df[df['id'] == id_alvo].iloc[0]

                with st.form("edit_form"):
                    n_desc = st.text_input("Alterar Descrição", value=d_at['category'])
                    n_valor_full = st.number_input("Alterar Valor Total", value=float(d_at['amount']) * int(d_at['installment_total']))
                    n_data_base = st.date_input("Alterar Data", pd.to_datetime(d_at['date']))
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 ATUALIZAR TUDO"):
                        relacionadas = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total']) & (df['type'] == d_at['type'])]
                        v_nova_parc = n_valor_full / int(d_at['installment_total'])
                        for idx, row in relacionadas.iterrows():
                            nova_data = add_months(n_data_base, int(row['installment_number']) - 1)
                            supabase.table("profile_transactions").update({"category": n_desc, "amount": round(v_nova_parc, 2), "date": nova_data.strftime("%Y-%m-%d")}).eq("id", row['id']).execute()
                        st.success("Atualizado!")
                        st.rerun()
                        
                    if c2.form_submit_button("🗑️ EXCLUIR REGISTRO"):
                        relacionadas = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total']) & (df['type'] == d_at['type'])]
                        for _, row in relacionadas.iterrows():
                            supabase.table("profile_transactions").delete().eq("id", row['id']).execute()
                        st.warning("Excluído.")
                        st.rerun()

        with tab_config:
            st.subheader("Configurações do App")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Gerenciar Cartões**")
                n_c = st.text_input("Nome do Novo Cartão")
                if st.button("Adicionar"):
                    if n_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                        st.rerun()
            with col_b:
                if lista_cartoes:
                    cart_del = st.selectbox("Remover Cartão", lista_cartoes)
                    if st.button("Excluir Cartão"):
                        supabase.table("my_cards").delete().eq("id", dict_cartoes[cart_del]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
