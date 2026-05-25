import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Header from "./assets/components/Header/Header.jsx";

import "./App.css";
import Login from "./assets/pages/Login/Login.jsx";
import RecuperarSenha from "./assets/pages/RecuperarSenha/RecuperarSenha.jsx";
import VerificarCodigo from "./assets/pages/VerificarCodigo/VerificarCodigo.jsx";
import ConfirmarCodigo from "./assets/pages/ConfirmarCodigo/ConfirmarCodigo.jsx";
import Footer from "./assets/components/Footer/Footer.jsx";
import Dashboard from "./assets/pages/Dashbord/Dashboard.jsx";
import AdicionarUsuario from "./assets/pages/AdicionarUsuario/AdicionarUsuario.jsx";
import Paginaerro from "./assets/pages/Paginaerro/Paginaerro.jsx";

function App() {
    return (
        <Router>
            <div className="app">
                <Header />
                <Routes>
                    <Route path="/" element={<Login />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/recuperar-senha" element={<RecuperarSenha />} />
                    <Route path="/verificar-codigo" element={<VerificarCodigo />} />
                    <Route path="/confirmar-codigo" element={<ConfirmarCodigo />} />
                    <Route path="/dashboard" element={< Dashboard />} />
                    <Route path="/adicionarusuarios" element={< AdicionarUsuario />} />
                    <Route path="*" element={< Paginaerro />} />
                </Routes>
                <Footer />
            </div>
        </Router>
    );
}

export default App;

