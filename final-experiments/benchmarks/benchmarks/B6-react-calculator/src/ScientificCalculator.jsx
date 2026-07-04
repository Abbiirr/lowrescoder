import React, { useState } from 'react';
import math from 'mathjs';

const ScientificCalculator = () => {
  const [expression, setExpression] = useState('');
  const [result, setResult] = useState('');

  const handleButtonClick = (value) => {
    if (value === '=') {
      try {
        setResult(math.evaluate(expression));
      } catch (error) {
        setResult('Error');
      }
    } else {
      setExpression((prev) => prev + value);
    }
  };

  return (
    <div className='bg-gray-800 text-white p-6'>
      <h2 className='text-2xl font-bold'>Scientific Calculator</h2>
      <div className='bg-gray-700 rounded-lg p-4 mb-4'>
        <div className='text-4xl font-mono'>{result}</div>
        <div className='text-sm text-gray-400'>{expression}</div>
      </div>
      <div className='grid grid-cols-4 gap-2'>
        {[...Array(36)].map((_, index) => {
          const value = [
            '7', '8', '9', '/', 'sqrt', 'sin', 'cos', 'tan',
            '4', '5', '6', '*', 'log', 'asin', 'acos', 'atan',
            '1', '2', '3', '-', '^', 'exp', 'abs', 'sign',
            '0', '.', '=', '+', '(', ')', 'pi', 'e'
          ][index];
          return (
            <button
              key={index}
              onClick={() => handleButtonClick(value)}
              className={`py-2 px-4 rounded-lg hover:bg-gray-600 active:scale-95 ${value === '=' ? 'bg-gradient-to-r from-green-500 to-blue-500 text-white' : value.match(/[*/+-^()]/) ? 'bg-orange-500 text-white' : 'bg-gray-700 text-white'}`}
            >
              {value}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ScientificCalculator;