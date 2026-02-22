import React from 'react';
import { NavLink } from 'react-router-dom';

const App = () => {
  return (
    <div className='flex'>
      <aside className='bg-gray-800 p-4 w-64 hidden md:block'>
        <nav>
          <NavLink to='/' activeClassName='bg-indigo-600 text-white' className='block py-2 px-3 rounded-lg mb-2 hover:bg-gray-700'>Home</NavLink>
          <NavLink to='/regular' activeClassName='bg-indigo-600 text-white' className='block py-2 px-3 rounded-lg mb-2 hover:bg-gray-700'>Regular Calculator</NavLink>
          <NavLink to='/scientific' activeClassName='bg-indigo-600 text-white' className='block py-2 px-3 rounded-lg mb-2 hover:bg-gray-700'>Scientific Calculator</NavLink>
          <NavLink to='/currency' activeClassName='bg-indigo-600 text-white' className='block py-2 px-3 rounded-lg mb-2 hover:bg-gray-700'>Currency Converter</NavLink>
          <NavLink to='/unit' activeClassName='bg-indigo-600 text-white' className='block py-2 px-3 rounded-lg mb-2 hover:bg-gray-700'>Unit Converter</NavLink>
        </nav>
      </aside>
      <main className='flex-grow bg-gray-800 p-4'>
        {/* Main content will be rendered here */}
      </main>
    </div>
  );
};

export default App;