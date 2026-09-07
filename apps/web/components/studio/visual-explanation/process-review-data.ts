import {ProcessScene} from './process-model';
export const processReviewScenes:ProcessScene[]=[
 {title:'What does a filter separate?',subtitle:'Follow the water. Notice which particles stay behind.',locale:'en',topology:'sequence',sourceLabel:'Authored explanation of basic filtration; ACS Water Filtration (2004). Not a drinking-water procedure.',sourceUrl:'https://pubs.acs.org/doi/10.1021/ed081p224A',stages:[
 {id:'mixture',label:'A mixture',detail:'Water carries suspended sand particles.',art:'drop'},
 {id:'filter',label:'Through the filter',detail:'The filter traps particles too large to pass through its openings.',art:'filter'},
 {id:'collected',label:'Collected water',detail:'Water passes through. Clearer water is not necessarily safe to drink.',art:'vessel'}],relations:[{id:'mixture-to-filter',from:'mixture',to:'filter',label:'Water flows into'},{id:'filter-to-collected',from:'filter',to:'collected',label:'Water passes into'}]},
 {title:'A butterfly’s life cycle',subtitle:'Four life stages. The return begins a new generation, not the same butterfly becoming an egg.',locale:'en',topology:'cycle',sourceLabel:'Florida Museum of Natural History · Butterfly Life Cycle. Schematic illustrations, not a species identification guide.',sourceUrl:'https://www.floridamuseum.ufl.edu/educators/resource/butterfly-life-cycle/',stages:[
 {id:'egg',label:'Egg',detail:'A female lays eggs on a suitable plant.',art:'egg'},
 {id:'larva',label:'Caterpillar',detail:'The larva hatches, feeds and grows.',art:'larva'},
 {id:'pupa',label:'Chrysalis',detail:'The butterfly develops inside the pupa.',art:'pupa'},
 {id:'adult',label:'Adult butterfly',detail:'The adult emerges. After mating, a female can lay eggs.',art:'butterfly'}],relations:[{id:'egg-to-larva',from:'egg',to:'larva',label:'Hatches into'},{id:'larva-to-pupa',from:'larva',to:'pupa',label:'Develops into'},{id:'pupa-to-adult',from:'pupa',to:'adult',label:'Adult emerges'},{id:'adult-to-egg',from:'adult',to:'egg',label:'Female lays eggs · new generation'}]},
 {title:'Give your idea a clear shape',subtitle:'One useful writing routine. Review can send us back to planning; this is a choice, not a rule for every writer.',locale:'en',topology:'cycle',sourceLabel:'Authored writing/revision review model; optional return to planning. Not a grammar assessment.',stages:[
 {id:'plan',label:'Plan',detail:'Choose a main idea and gather supporting details.',art:'idea'},
 {id:'draft',label:'Draft',detail:'Put the idea into sentences. It does not need to be perfect yet.',art:'draft'},
 {id:'review',label:'Review & revise',detail:'Read for meaning. Change wording or rethink the plan if the idea needs it.',art:'review'}],relations:[{id:'plan-to-draft',from:'plan',to:'draft',label:'Turn ideas into sentences'},{id:'draft-to-review',from:'draft',to:'review',label:'Read and improve'},{id:'review-to-plan',from:'review',to:'plan',label:'Return if the idea needs rethinking'}]}
];
export function reviewScene(index:number,arabic:boolean,longLabels=false):ProcessScene {
 const base=processReviewScenes[index];
 const translations=[
 {title:'كيف يفصل المرشّح مكوّنات الخليط؟',subtitle:'تتبّع الماء ولاحظ الجسيمات التي تبقى في المرشّح.',labels:['خليط الماء والرمل','المرور عبر المرشّح','الماء المتجمّع'],details:['يحمل الماء جسيمات رمل عالقة.','تُحتجز الجسيمات الأكبر من فتحات المرشّح.','يمرّ الماء، لكن صفاءه لا يعني أنه صالح للشرب.'],relations:['يتدفّق الماء إلى','يمرّ الماء إلى']},
 {title:'دورة حياة الفراشة',subtitle:'أربع مراحل. تبدأ العودة جيلًا جديدًا؛ لا تتحوّل الفراشة نفسها إلى بيضة.',labels:['البيضة','اليرقة (Caterpillar)','العذراء','الفراشة البالغة'],details:['تضع الأنثى البيض على نبات مناسب.','تفقس اليرقة وتتغذّى وتنمو.','تتطوّر الفراشة داخل العذراء.','تخرج الفراشة البالغة؛ وبعد التزاوج قد تضع الأنثى البيض.'],relations:['تفقس إلى','تتطوّر إلى','تخرج الفراشة','تضع الأنثى البيض — جيل جديد']},
 {title:'من فكرة إلى نصّ واضح',subtitle:'طريقة ممكنة للكتابة. قد نعود إلى التخطيط عند الحاجة، وليست هذه قاعدة لكلّ كاتب.',labels:['أخطّط للفكرة','أكتب المسوّدة (Draft)','أراجع وأعدّل'],details:['أختار فكرة رئيسة وأجمع التفاصيل التي تدعمها.','أحوّل الفكرة إلى جمل، ولا يشترط أن تكون مثالية من البداية.','أقرأ المعنى وأحسّن الصياغة، أو أعيد التفكير في الخطّة عند الحاجة.'],relations:['أحوّل الأفكار إلى جمل','أقرأ وأحسّن','أعود إذا احتاجت الفكرة إلى تخطيط جديد']}
 ][index];
 const result:ProcessScene=arabic?{...base,locale:'ar',title:translations.title,subtitle:translations.subtitle,stages:base.stages.map((s,i)=>({...s,label:translations.labels[i],detail:translations.details[i]})),relations:base.relations.map((r,i)=>({...r,label:translations.relations[i]}))}:base;
 return longLabels?{...result,stages:result.stages.map(s=>({...s,label:s.label+(arabic?' — مرحلة لقراءة التفاصيل بعناية':' — a stage to examine closely')}))}:result;
}
