import styles from "../../../styles/Header.module.css";
import logo from "../../../public/logo.png";

function Header() {

    const handleLogout = async () => {
        // Chama o endpoint de logout no backend para remover o cookie httponly
        await fetch("http://127.0.0.1:5000/logout", {
            method: "POST",
            credentials: "include"
        });

        // Limpa dados locais
        localStorage.removeItem('usuario');
        localStorage.removeItem('logado');
        localStorage.removeItem('email_recuperacao');
        localStorage.removeItem('codigo_recuperacao');

        window.location.href = '/login';
    };

    return (
        <header className={styles.header}>
            <div className={styles.logoContainer}>
                <img src={logo} alt="Top Lanches" className={styles.logo} />
            </div>
            <nav>
                <ul className={styles.navList}>
                    <li><a href="/" className={styles.navLink}>Início</a></li>
                    <li><a href="/cardapio" className={styles.navLink}>Cardápio</a></li>
                    <li><a href="/contato" className={styles.navLink}>Contato</a></li>
                    <li>
                        <button onClick={handleLogout} className={styles.logoutBtn}>
                            Sair
                        </button>
                    </li>
                </ul>
            </nav>
        </header>
    );
}

export default Header;