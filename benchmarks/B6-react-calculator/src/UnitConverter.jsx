import React, { useState } from 'react';

const UnitConverter = () => {
  const [value, setValue] = useState('');
  const [fromUnit, setFromUnit] = useState('m');
  const [toUnit, setToUnit] = useState('cm');
  const [result, setResult] = useState('');

  const conversionRates = {
    m: { cm: 100, in: 39.37, ft: 3.28 },
    cm: { m: 0.01, in: 0.3937, ft: 0.0328 },
    in: { m: 0.0254, cm: 2.54, ft: 0.0833 },
    ft: { m: 0.3048, cm: 30.48, in: 12 }
  };

  const handleConvert = () => {
    const rate = conversionRates[fromUnit][toUnit];
    setResult((value * rate).toFixed(2));
  };

  return (
    <div className='bg-gray-800 text-white p-6'>
      <h2 className='text-2xl font-bold'>Unit Converter</h2>
      <div className='bg-gray-700 rounded-lg p-4 mb-4'>
        <div className='text-4xl font-mono'>{result}</div>
      </div>
      <div className='grid grid-cols-2 gap-2'>
        <input
          type='number'
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder='Value'
          className='py-2 px-4 rounded-lg bg-gray-700 text-white'
        />
        <select
          value={fromUnit}
          onChange={(e) => setFromUnit(e.target.value)}
          className='py-2 px-4 rounded-lg bg-gray-700 text-white'
        >
          <option value='m'>Meter (m)</option>
          <option value='cm'>Centimeter (cm)</option>
          <option value='in'>Inch (in)</option>
          <option value='ft'>Foot (ft)</option>
        </select>
        <select
          value={toUnit}
          onChange={(e) => setToUnit(e.target.value)}
          className='py-2 px-4 rounded-lg bg-gray-700 text-white'
        >
          <option value='m'>Meter (m)</option>
          <option value='cm'>Centimeter (cm)</option>
          <option value='in'>Inch (in)</option>
          <option value='ft'>Foot (ft)</option>
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

export default UnitConverter;