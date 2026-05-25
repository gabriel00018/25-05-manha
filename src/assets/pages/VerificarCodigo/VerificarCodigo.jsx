import { useState } from 'react';
import { Link } from 'react-router-dom';
import styles from "../../../styles/VerificarCodigo.module.css";

function VerificarCodigo() {
    const [codigo, setCodigo] = useState('');
    const [mensagem, setMensagem] = useState('');
    const [erro, setErro] = useState('');
    const [carregando, setCarregando] = useState(false);
    const [senha, setSenha] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMensagem('');
        setErro('');
        setCarregando(true);

        const response = await fetch('http://127.0.0.1:5000/confirmar_codigo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: localStorage.getItem('email_recuperacao'),
                codigo: codigo,
                senha: senha
            })
        });

        var data = await response.json();

        if (response.ok) {
            setMensagem('Código verificado! Redirecionando...');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else {
            setErro(data.erro || 'Código inválido. Tente novamente.');
        }
        setCarregando(false);
    };

    return (
        <div className={styles.pageContainer}>
            <div className={styles.verificationCard}>
                <h2 className={styles.title}>Recuperação de senha</h2>

                {mensagem && <div className={styles.successMessage}>{mensagem}</div>}
                {erro && <div className={styles.errorMessage}>{erro}</div>}

                <form onSubmit={handleSubmit}>
                    <div className={styles.formGroup}>
                        <label>Código de verificação</label>
                        <input
                            type="text"
                            placeholder="Insira o código de verificação"
                            value={codigo}
                            onChange={(e) => setCodigo(e.target.value)}
                            maxLength={6}
                            required
                        />
                    </div>

                    <div className={styles.formGroup}>
                        <label>Código de verificação</label>
                        <input
                            type="password"
                            placeholder="Insira sua nova senha"
                            value={senha}
                            onChange={(e) => setSenha(e.target.value)}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className={styles.sendBtn}
                        disabled={carregando}
                    >
                        enviar
                    </button>
                </form>
            </div>
        </div>
    );
}

export default VerificarCodigo;