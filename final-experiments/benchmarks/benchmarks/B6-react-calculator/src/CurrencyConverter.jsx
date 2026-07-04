import React, { useState } from 'react';
import axios from 'axios';

const CurrencyConverter = () => {
  const [amount, setAmount] = useState('');
  const [fromCurrency, setFromCurrency] = useState('USD');
  const [toCurrency, setToCurrency] = useState('EUR');
  const [result, setResult] = useState('');

  const handleConvert = async () => {
    try {
      const response = await axios.get(`https://api.exchangerate-api.com/v4/latest/${fromCurrency}`);
      const rate = response.data.rates[toCurrency];
      setResult((amount * rate).toFixed(2));
    } catch (error) {
      setResult('Error');
    }
  };

  return (
    <div className='bg-gray-800 text-white p-6'>
      <h2 className='text-2xl font-bold'>Currency Converter</h2>
      <div className='bg-gray-700 rounded-lg p-4 mb-4'>
        <div className='text-4xl font-mono'>{result}</div>
      </div>
      <div className='grid grid-cols-2 gap-2'>
        <input
          type='number'
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder='Amount'
          className='py-2 px-4 rounded-lg bg-gray-700 text-white'
        />
        <select
          value={fromCurrency}
          onChange={(e) => setFromCurrency(e.target.value)}
          className='py-2 px-4 rounded-lg bg-gray-700 text-white'
        >
          <option value='USD'>USD</option>
          <option value='EUR'>EUR</option>
          <option value='JPY'>JPY</option>
          {/* Add more currencies */}
        </select>
        <select
          value={toCurrency}
          onChange={(e) => setToCurrency(e.target.value)}
          className='py-2 px-4 rounded-lg bg-gray-700 text-white'
        >
          <option value='USD'>USD</option>
          <option value='EUR'>EUR</option>
          <option value='JPY'>JPY</option>
          {/* Add more currencies */}
        </select>
        <button
          onClick={handleConvert}
          className='py-2 px-4 rounded-lg bg-gradient-to-r from-green-500 to-blue-500 text-white hover:bg-gray-600 active:scale-95'
        >
          Convert
        </button>
      </div>
    </div>
  );
};

export default CurrencyConverter;