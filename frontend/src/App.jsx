import React from 'react';
import { Provider } from 'react-redux';
import { store } from './app/store';
import Header from './components/Layout/Header';
import ComplaintPage from './pages/ComplaintPage';

export default function App() {
  return (
    <Provider store={store}>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
        <Header />
        <ComplaintPage />
      </div>
    </Provider>
  );
}
