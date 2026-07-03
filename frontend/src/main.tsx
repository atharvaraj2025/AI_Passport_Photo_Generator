import React from 'react'; import ReactDOM from 'react-dom/client'; import { QueryClient, QueryClientProvider } from '@tanstack/react-query'; import App from './App'; import { ThemeProvider } from './contexts/ThemeContext'; import './index.css';
const client = new QueryClient();
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><ThemeProvider><App/></ThemeProvider></QueryClientProvider></React.StrictMode>);
