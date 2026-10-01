// Game scenery is trusted local artwork, never user-provided markup.
const scenery = {
  robot: [
    '<path d="M32 305h170v125H32z" fill="#203e55" stroke="#71c7d5" stroke-width="4"/><path d="M55 329h122v42H55z" fill="#123047"/><path d="m69 349 20-9 18 17 27-14 26 10" stroke="#78efcc" stroke-width="4" fill="none"/><path d="M57 395h118" stroke="#4f9aa6" stroke-width="8"/>',
    '<path d="M603 83h170v213H603z" rx="5" fill="#20394e" stroke="#b1dfec" stroke-width="5"/><path d="M617 99h142v178H617z" fill="#142437"/><path d="M625 128h126M625 201h126" stroke="#74bace"/><g fill="#7dddca"><circle cx="640" cy="113" r="3"/><circle cx="742" cy="145" r="2"/></g><path d="m648 263 22-100h36l27 100z" fill="#8cafc3"/><path d="M651 167h62v15h-62z" fill="#89eee8"/>',
  ],
  cat: [
    '<path d="M42 155h163v125H42z" fill="#173341" stroke="#badbd9" stroke-width="7"/><path d="M48 211q39-38 75-18t75-29v109H48z" fill="#68967e"/><path d="M123 158v117" stroke="#d3e7e3" stroke-width="5"/><path d="M49 279h150v12H49z" fill="#a5bbab"/>',
    '<path d="M591 60h183v233H591z" fill="#769dab" stroke="#cbdfe8" stroke-width="5"/><path d="M611 201v-53h27v53h15V91h35v110h17v-79h25v79h33v70H607z" fill="#334960"/><path d="M654 63v226M594 217h177" stroke="#d5e7ec" stroke-width="5"/><path d="M579 286h207v14H579z" fill="#a1bbce"/>',
  ],
  dragon: [
    '<path d="M45 337q0-38 38-38h98q38 0 38 38v76H45z" fill="#ae8853" stroke="#f5d783" stroke-width="5"/><path d="M47 345h169M77 302v110M188 302v110" stroke="#eacf86" stroke-width="6"/><path d="M117 340h30v24h-30z" fill="#ffe8a1"/><g fill="#ecd66c"><ellipse cx="51" cy="423" rx="20" ry="6"/><ellipse cx="83" cy="417" rx="21" ry="7"/></g>',
    '<path d="M586 314V138h29v24h21v-24h29v24h21v-24h29v24h21v-24h28v190z" fill="#6c7b8d" stroke="#b1bfcd" stroke-width="4"/><path d="M605 309V198h43v111M707 309V198h43v111" fill="#394b61"/><path d="M657 306v-66q0-23 20-23t20 23v66z" fill="#efd28b"/><path d="M586 178h179M586 278h179" stroke="#9dabb9" stroke-width="3"/>',
  ],
  penguin: [
    '<path d="M47 365q8-90 97-90t97 90v65H47z" fill="#a6d7e2" stroke="#dcffff" stroke-width="4"/><path d="M57 334h174M72 308h145M111 282v148M175 282v148" stroke="#79b4c6" stroke-width="3"/><path d="M111 430v-61q0-25 27-25t27 25v61z" fill="#264f71"/>',
    '<path d="M580 343V199l36-72 35 72v81h29V168l32-73 32 73v112h28v68z" fill="#90cbdc" stroke="#d9ffff" stroke-width="4"/><path d="M615 209v61M711 177v80M649 302h59" stroke="#d0faff" stroke-width="9"/><path d="M657 343v-26q0-17 16-17t16 17v26z" fill="#30789b"/>',
  ],
  owl: [
    '<path d="M53 331V218h137v119z" fill="#536c68" stroke="#b3c7a0" stroke-width="5"/><path d="m38 219 84-65 85 65z" fill="#86a998" stroke="#c7dcab" stroke-width="4"/><path d="M96 265h50v62H96z" fill="#f4d899"/><path d="M66 243h25v29H66z" fill="#93d8d9"/>',
    '<path d="M638 327V145h108v182z" fill="#4d5375" stroke="#a9abc9" stroke-width="4"/><path d="m620 147 72-104 73 104z" fill="#7685a8" stroke="#e3d18d" stroke-width="4"/><path d="M669 328v-48q0-21 24-21t24 21v48zM674 186v-15q0-14 18-14t18 14v15z" fill="#f5d991"/><path d="M633 237h117" stroke="#99b5ca" stroke-width="4"/><path d="m687 49 5-16 5 16 16 5-16 5-5 16-5-16-16-5z" fill="#e8edb1"/>',
  ],
};

export function roomEvolution(pet) {
  const [second, third] = scenery[pet] || scenery.robot;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><g class="evolution-two">${second}</g><g class="evolution-three">${third}</g></svg>`;
}
