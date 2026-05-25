import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from "../../../styles/Dashboard.module.css";
import { Link } from "react-router-dom";

export default function Dashboard() {
    const navigate = useNavigate();
    const [user, setUser] = useState({});
    const [usuarios, setUsuarios] = useState([]);
    const [loading, setLoading] = useState(true);
    const [erro, setErro] = useState('');

    useEffect(() => {
        const usuarioStr = localStorage.getItem("usuario");
        if (!usuarioStr) {
            navigate('/login');
            return;
        }
        const usuarioObj = JSON.parse(usuarioStr);
        setUser(usuarioObj);

        fetch('http://127.0.0.1:5000/usuarios', {
            method: 'GET',
            credentials: 'include',
        })
            .then(res => {
                if (!res.ok) {
                    return res.json().then(errorData => {
                        throw new Error(errorData.erro || res.statusText || 'Erro ao carregar lista de usuários');
                    }).catch(() => {
                        throw new Error(res.statusText || 'Erro ao carregar lista de usuários');
                    });
                }
                return res.json();
            })
            .then(data => {
                setUsuarios(data);
                setLoading(false);
            })
            .catch(err => {
                console.error('Fetch error:', err);
                setErro(err.message);
                setLoading(false);
            });
    }, [navigate]);

    // ✅ Função para desbloquear usuário
    const desbloquear = async (id) => {
        try {
            const res = await fetch(`http://127.0.0.1:5000/admin/desbloquear/${id}`, {
                method: 'POST',
                credentials: 'include',
            });
            if (res.ok) {
                setUsuarios(prev =>
                    prev.map(u => u.id === id ? { ...u, bloqueado: 'Não' } : u)
                );
            } else {
                alert('Erro ao desbloquear usuário');
            }
        } catch {
            alert('Erro de conexão');
        }
    };

    return (
        <div className={styles.dashboardContainer}>
            <h1>Olá, {user.nome}</h1>

            <h2 className={styles.sectionTitle}>Usuários</h2>

            <aside className={styles.sidebar}>
                <nav>
                    <ul>
                        <li><a href="/adicionarlanches">Adicionar Lanches</a></li>
                        {user.id_tipo === 1 && (
                            <li><a href="/adicionarusuarios">Adicionar Usuarios</a></li>
                        )}
                        <li><a href="/adicionarmesas">Adicionar Mesas</a></li>
                        <li><a href="/adicionarcategoria">Adicionar Categoria</a></li>
                    </ul>
                </nav>
            </aside>

            <div className={styles.cardsGrid}>
                {loading && <p className={styles.loadingText}>Carregando usuários...</p>}
                {erro && <p className={styles.errorText}>{erro}</p>}
                {!loading && !erro && usuarios.map(u => (
                    <div key={u.id} className={styles.card}>
                        <div className={styles.cardHeader}>
                            <h3>{u.nome}</h3>
                            <span className={`${styles.badge} ${u.tipo === 'admin' ? styles.badgeAdmin : styles.badgeGarcom}`}>
                                {u.tipo === 'admin' ? 'ADM' : 'Garçom'}
                            </span>
                        </div>
                        <p className={styles.cardEmail}>{u.email}</p>
                        <div className={styles.cardMeta}>
                            <span className={`${styles.badge} ${u.bloqueado === 'Sim' ? styles.badgeBloqueado : styles.badgeAtivo}`}>
                                {u.bloqueado === 'Sim' ? 'Bloqueado' : 'Ativo'}
                            </span>

                            {/* ✅ Botão só aparece para ADM e só se o usuário estiver bloqueado */}
                            {user.id_tipo === 1 && u.bloqueado === 'Sim' && (
                                <button
                                    className={styles.btnDesbloquear}
                                    onClick={() => desbloquear(u.id)}
                                >
                                    Desbloquear
                                </button>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}