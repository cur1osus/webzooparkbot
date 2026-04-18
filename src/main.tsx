import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './tma'; // Инициализация TMA SDK + вызов ready() как можно раньше
import App from './App.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
