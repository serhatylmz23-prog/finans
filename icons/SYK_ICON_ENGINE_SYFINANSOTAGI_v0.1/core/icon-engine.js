
export class SykIconEngine {
 constructor(states){this.states=states;}
 getState(s){return this.states[s]||this.states.passive;}
 clampProgress(v){return Math.max(0,Math.min(100,Number(v)||0));}
 progressOffset(p,c=226){return c-(c*this.clampProgress(p)/100);}
}
