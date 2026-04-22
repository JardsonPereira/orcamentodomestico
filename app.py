import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

# --- CONFIGURAÇÕES E BANCO DE DATA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()

def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')

def add_userdata(username, password):
    c.execute('INSERT INTO userstable(username, password) VALUES (?,?)', (username, password))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    return data

def create_financetable(username):
    # Cria uma tabela específica ou usa uma coluna de usuário para filtrar
    c.execute(f'CREATE TABLE IF NOT EXISTS transactions_{username}(type TEXT, category TEXT, amount REAL, date TEXT)')
    conn.commit()

# --- INTERFACE ---
def main():
    st.set_page_config(page_title="Controle Financeiro", layout="centered")
    st.title("💰 Gestão de Despesas e Receitas")

    menu = ["Home", "Login", "Cadastro"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.subheader("Bem-vindo ao seu App Financeiro")
        st.info("Faça o login para gerenciar suas contas.")

    elif choice == "Cadastro":
        st.subheader("Criar Nova Conta")
        new_user = st.text_input("Usuário")
        new_password = st.text_input("Senha", type='password')

        if st.button("Cadastrar"):
            create_usertable()
            add_userdata(new_user, make_hashes(new_password))
            st.success("Conta criada com sucesso!")
            st.info("Vá para o menu de Login.")

    elif choice == "Login":
        st.subheader("Login de Usuário")
        username = st.sidebar.text_input("Usuário")
        password = st.sidebar.text_input("Senha", type='password')

        if st.sidebar.checkbox("Entrar"):
            create_usertable()
            hashed_pswd = make_hashes(password)
            result = login_user(username, hashed_pswd)

            if result:
                st.success(f"Logado como {username}")
                create_financetable(username)

                # --- ÁREA DO USUÁRIO ---
                tab1, tab2, tab3 = st.tabs(["Lançamentos", "Histórico", "Resumo"])

                with tab1:
                    st.markdown("### Novo Lançamento")
                    tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
                    cat = st.text_input("Categoria (Ex: Aluguel, Salário, Alimentação)")
                    valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
                    data = st.date_input("Data", datetime.now())

                    if st.button("Salvar Registro"):
                        c.execute(f'INSERT INTO transactions_{username} VALUES (?,?,?,?)', 
                                 (tipo, cat, valor, data.strftime("%Y-%m-%d")))
                        conn.commit()
                        st.success("Registrado!")

                with tab2:
                    st.markdown("### Seus Dados")
                    df = pd.read_sql_query(f"SELECT * FROM transactions_{username}", conn)
                    st.dataframe(df, use_container_width=True)

                with tab3:
                    df = pd.read_sql_query(f"SELECT * FROM transactions_{username}", conn)
                    if not df.empty:
                        receita_total = df[df['type'] == 'Receita']['amount'].sum()
                        despesa_total = df[df['type'] == 'Despesa']['amount'].sum()
                        saldo = receita_total - despesa_total

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Receitas", f"R$ {receita_total:,.2f}")
                        col2.metric("Despesas", f"R$ {despesa_total:,.2f}")
                        col3.metric("Saldo", f"R$ {saldo:,.2f}", delta=saldo)
                    else:
                        st.warning("Nenhum dado cadastrado.")

            else:
                st.warning("Usuário ou senha incorretos.")

if __name__ == '__main__':
    main()
