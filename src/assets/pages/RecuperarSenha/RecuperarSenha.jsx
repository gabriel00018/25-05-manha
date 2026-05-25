import { useState } from 'react';
import { Link } from 'react-router-dom';
import styles from "../../../styles/RecuperarSenha.module.css";

function RecuperarSenha() {
    const [email, setEmail] = useState('');
    const [mensagem, setMensagem] = useState('');
    const [erro, setErro] = useState('');
    const [carregando, setCarregando] = useState(false);


    async function recuperaSenha() {
        var resposta = await fetch("http://127.0.0.1:5000/solicitar_recuperacao", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "include",
            body: JSON.stringify({
                email: email,

            })
        })

        resposta = await resposta.json();

        console.log(resposta);

        localStorage.setItem('email_recuperacao', email);

        // Simulação
        setTimeout(() => {
            setMensagem(`Código enviado para ${email}!`);
            setTimeout(() => {
                window.location.href = '/verificar-codigo';
            }, 2000);
            setCarregando(false);
        }, 1500);
    }



    return (
        <div className={styles.pageContainer}>
            <div className={styles.recoveryCard}>
                <h2 className={styles.title}>Recuperação de senha</h2>

                {mensagem && <div className={styles.successMessage}>{mensagem}</div>}
                {erro && <div className={styles.errorMessage}>{erro}</div>}

                <div>
                    <div className={styles.formGroup}>
                        <label>Email:</label>
                        <input
                            type="email"
                            placeholder="Insira seu E-mail"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className={styles.sendBtn}
                        onClick={recuperaSenha}
                    >
                        enviar
                    </button>

                    <Link to="/login" className={styles.backLink}>
                        Voltar para o login
                    </Link>
                </div>
            </div>
        </div>
    );
}

export default RecuperarSenha;