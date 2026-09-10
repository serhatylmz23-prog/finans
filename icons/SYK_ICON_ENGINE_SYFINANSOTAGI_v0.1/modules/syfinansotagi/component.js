
import symbols from './symbols.json' assert {type:'json'};

export function createFinanceIcon(name,state='active',progress=0){
 return {
   module:'SyFinansOtağı',
   name,
   symbol:symbols[name] || 'finance',
   state,
   progress
 };
}
