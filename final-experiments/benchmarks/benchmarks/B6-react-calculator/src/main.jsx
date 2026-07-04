import React from 'react';
import ReactDOM from 'react-dom';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './index.css';

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path='/' element={<LandingPage />} />
        <Route path='/regular' element={<RegularCalculator />} />
        <Route path='/scientific' element={<ScientificCalculator />} />
        <Route path='/currency' element={<CurrencyConverter />} />
        <Route path='/unit' element={<UnitConverter />} />
      </Routes>
    </Router>
  );
};

const LandingPage = () => {
  return (
    <div className='bg-gray-800 text-white p-6'>
      <h1 className='text-3xl font-bold'>Welcome to the Calculator App</h1>
      <p>Select a calculator from the sidebar.</p>
    </div>
  );
};

const RegularCalculator = () => {
  return (
    <div className='bg-gray-800 text-white p-6'>
      <h2 className='text-2xl font-bold'>Regular Calculator</h2>
      {/* Calculator implementation */}
    </div>
  );
};

const ScientificCalculator = () => {
  return (
    <div className='bg-gray-800 text-white p-6'>
      <h2 className='text-2xl font-bold'>Scientific Calculator</h2>
      {/* Calculator implementation */}
    </div>
  );
};

const CurrencyConverter = () => {
  return (
    <div className='bg-gray-800 text-white p-6'>
      <h2 className='text-2xl font-bold'>Currency Converter</h2>
      {/* Converter implementation */}
    </div>
  );
};

const UnitConverter = () => {
  return (
    <div className='bg-gray-800 text-white p-6'>
      <h2 className='text-2xl font-bold'>Unit Converter</h2>
      {/* Converter implementation */}
    </div>
  );
};

ReactDOM.render(<App />, document.getElementById('root'));