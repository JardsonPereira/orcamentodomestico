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
    st.session_state.user_name = "Usuário"
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

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
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #F0F2F5; }
        
        @media (max-width: 640px) {
            .stMetric { padding: 10px !important; }
            .stMetric div { font-size: 0.8rem !important; }
            .stTabs [data-baseweb="tab-list"] { gap: 8px; }
            .stTabs [data-baseweb="tab"] { padding: 8px 4px; font-size: 12px; }
        }
        
        .stButton>button {
            width: 100%; border-radius: 10px; height: 3.2em;
            font-weight: 600; transition: all 0.2s;
        }
        
        [data-testid="stExpander"], div[data-testid="stForm"], .stContainer { 
            background: white; border-radius: 12px; border: 1px solid #eee; padding: 15px; margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.logado:
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        
        with col_central:
            escolha = st.radio("Acesso", ["Entrar na Conta", "Criar Nova Conta", "Recuperar Senha"], horizontal=True, label_visibility="collapsed")
            
            with st.container():
                if escolha == "Entrar na Conta":
                    st.subheader("Login")
                    email = st.text_input("E-mail", placeholder="seu@email.com")
                    senha = st.text_input("Senha", type='password')
                    
                    if st.button("ACESSAR SISTEMA"):
                        try:
                            response = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            if response.user:
                                st.session_state.logado = True
                                st.session_state.user_email = email
                                # O nome será buscado ou ficará como Usuário por padrão no login
                                st.rerun()
                        except:
                            st.error("Erro no login. Verifique se o e-mail/senha estão corretos.")
                            
                elif escolha == "Criar Nova Conta":
                    st.subheader("Cadastro")
                    novo_nome = st.text_input("Seu Nome", placeholder="Ex: Jardson")
                    novo_email = st.text_input("E-mail", placeholder="seu@email.com")
                    nova_senha = st.text_input("Crie uma senha", type='password', placeholder="mínimo 6 caracteres")
                    
                    if st.button("CRIAR MINHA CONTA"):
                        if not novo_nome or not novo_email or len(nova_senha) < 6:
                            st.warning("Preencha todos os campos corretamente.")
                        else:
                            try:
                                res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                                if res.user:
                                    st.session_state.logado = True
                                    st.session_state.user_email = novo_email
                                    st.session_state.user_name = novo_nome
                                    st.success("Conta criada! Acessando...")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao cadastrar: {str(e)}")

                else:
                    st.subheader("Recuperação de Senha")
                    email_rec = st.text_input("Digite seu e-mail cadastrado", placeholder="seu@email.com")
                    if st.button("ENVIAR E-MAIL DE RECUPERAÇÃO"):
                        try:
                            supabase.auth.reset_password_for_email(email_rec)
                            st.success("E-mail enviado! Verifique sua caixa de entrada para redefinir a senha.")
                        except Exception as e:
                            st.error(f"Erro ao enviar: {str(e)}")

    else:
        # --- SISTEMA LOGADO ---
        col_title, col_user = st.columns([3, 1])
        with col_title:
            nome_display = st.session_state.get('user_name', 'Usuário')
            st.title(f"💰 Olá, {nome_display}")
        with col_user:
            with st.expander(f"👤 Perfil"):
                st.write(f"Conectado como: {st.session_state.user_email}")
                if st.button("Encerrar Sessão"):
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
            st.subheader("Nova Movimentação")
            metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
            cart_v = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes: cart_v = st.selectbox("Qual Cartão?", lista_cartoes)
                else: st.warning("Cadastre um cartão primeiro.")

            with st.form("form_lanca", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                desc = st.text_input("Descrição")
                valor_t = st.number_input("Valor (R$)", min_value=0.01, step=0.10)
                data_o = st.date_input("Data", datetime.now())
                total_p = 1
                if metodo_sel == "Cartão de Crédito":
                    total_p = st.number_input("Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 SALVAR"):
                    u_email = st.session_state.user_email
                    v_parc = valor_t / int(total_p)
                    for i in range(int(total_p)):
                        d_venc = add_months(data_o, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parc, 2), "date": d_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_sel, "card_name": cart_v,
                            "installment_total": int(total_p), "installment_number": i + 1
                        }).execute()
                    st.success("✅ Lançado!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                mes_sel = st.radio("Meses", meses, index=len(meses)-1, horizontal=True, label_visibility="collapsed")
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                rec = f[f['type'] == 'Receita']['amount'].sum()
                des = f[f['type'] == 'Despesa']['amount'].sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Receitas", f"R$ {rec:,.2f}")
                m2.metric("Despesas", f"R$ {des:,.2f}")
                m3.metric("Saldo", f"R$ {rec-des:,.2f}")

                st.markdown("---")
                col_r, col_d = st.columns(2)
                with col_r:
                    st.markdown("### 🟢 Receitas")
                    df_r = f[f['type'] == 'Receita'][['date', 'category', 'amount']].copy()
                    df_r['date'] = df_r['date'].dt.strftime('%d/%m')
                    df_r['amount'] = df_r['amount'].apply(lambda x: f"R$ {x:,.2f}")
                    st.dataframe(df_r, use_container_width=True, hide_index=True)
                with col_d:
                    st.markdown("### 🔴 Despesas")
                    df_d = f[f['type'] == 'Despesa'].copy()
                    def fmt_p(row):
                        if row['payment_method'] == "Cartão de Crédito":
                            at, tot = int(row['installment_number']), int(row['installment_total'])
                            return f"{at}/{tot} (Faltam {tot-at})"
                        return "À vista"
                    df_d['Info'] = df_d.apply(fmt_p, axis=1)
                    df_d['amount'] = df_d['amount'].apply(lambda x: f"R$ {x:,.2f}")
                    st.dataframe(df_d[['date', 'category', 'amount', 'Info']], use_container_width=True, hide_index=True)
            else: st.info("Sem dados.")

        with tab_cartao:
            if not df.empty and lista_cartoes:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                df_c['date'] = pd.to_datetime(df_c['date'])
                for c in lista_cartoes:
                    with st.container():
                        st.subheader(f"💳 {c}")
                        dados = df_c[df_c['card_name'] == c]
                        if not dados.empty:
                            fat = dados[dados['date'].dt.strftime('%m/%Y') == datetime.now().strftime('%m/%Y')]['amount'].sum()
                            st.metric("Fatura do Mês", f"R$ {fat:,.2f}")
                            resumo = []
                            for (desc, total), grupo in dados.groupby(['category', 'installment_total']):
                                proximas = grupo[grupo['date'] >= datetime.now().replace(day=1)]
                                if not proximas.empty:
                                    resumo.append({
                                        'Venc.': proximas.iloc[0]['date'].strftime('%d/%m'),
                                        'Item': desc,
                                        'Parc.': f"{int(proximas.iloc[0]['installment_number'])}/{int(total)}",
                                        'Valor': f"R$ {proximas.iloc[0]['amount']:,.2f}"
                                    })
                            if resumo: st.table(pd.DataFrame(resumo))
            else: st.info("Nenhum cartão.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                df_edit['card_name'] = df_edit['card_name'].fillna('N/A')
                df_grouped = df_edit.sort_values(['category', 'card_name', 'installment_total', 'date'])
                df_grouped = df_grouped.groupby(['category', 'card_name', 'installment_total', 'payment_method', 'type'], as_index=False, dropna=False).first()
                
                opcoes = {}
                for _, r in df_grouped.iterrows():
                    v_total = float(r['amount']) * int(r['installment_total'])
                    prefixo = "💰" if r['type'] == 'Receita' else "💸"
                    label = f"{prefixo} {r['date'].strftime('%d/%m/%y')} | {r['category']} - R$ {v_total:,.2f}"
                    opcoes[label] = r['id']
                
                item_sel = st.selectbox("Selecione para editar", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                d_at = df[df['id'] == id_alvo].iloc[0]

                with st.form("edit_form"):
                    n_desc = st.text_input("Descrição", value=d_at['category'])
                    n_val_f = st.number_input("Valor Total (R$)", value=float(d_at['amount']) * int(d_at['installment_total']))
                    n_data_b = st.date_input("Data Original", pd.to_datetime(d_at['date']))
                    
                    if st.form_submit_button("💾 ATUALIZAR TUDO"):
                        rel = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total']) & (df['type'] == d_at['type'])]
                        v_np = n_val_f / int(d_at['installment_total'])
                        for idx, row in rel.iterrows():
                            nova_d = add_months(n_data_b, int(row['installment_number']) - 1)
                            supabase.table("profile_transactions").update({"category": n_desc, "amount": round(v_np, 2), "date": nova_d.strftime("%Y-%m-%d")}).eq("id", row['id']).execute()
                        st.rerun()
                    if st.form_submit_button("🗑️ EXCLUIR TUDO"):
                        rel = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total']) & (df['type'] == d_at['type'])]
                        for _, row in rel.iterrows():
                            supabase.table("profile_transactions").delete().eq("id", row['id']).execute()
                        st.rerun()

        with tab_config:
            st.subheader("Ajustes")
            col_a, col_b = st.columns(2)
            with col_a:
                n_c = st.text_input("Novo Cartão")
                if st.button("Adicionar Cartão"):
                    if n_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                        st.rerun()
            with col_b:
                if lista_cartoes:
                    c_del = st.selectbox("Remover", lista_cartoes)
                    if st.button("Excluir Cartão"):
                        supabase.table("my_cards").delete().eq("id", dict_cartoes[c_del]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
