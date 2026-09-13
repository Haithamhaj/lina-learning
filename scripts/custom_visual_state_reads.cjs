// Resolve only literal/const state IDs through lexical symbols; never execute source.
// Dynamic expressions are left to actual semantic events and replay verification.
const ts=require('typescript');
function staticBridgeStateReads(source){
 const file=ts.createSourceFile('visual.js',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
 const host={getSourceFile:n=>n==='visual.js'?file:undefined,getDefaultLibFileName:()=>'',writeFile:()=>{},getCurrentDirectory:()=>'',getDirectories:()=>[],fileExists:n=>n==='visual.js',readFile:n=>n==='visual.js'?source:undefined,getCanonicalFileName:n=>n,useCaseSensitiveFileNames:()=>true,getNewLine:()=> '\n'};
 const checker=ts.createProgram(['visual.js'],{allowJs:true,noLib:true,noResolve:true},host).getTypeChecker();
 const result=[];
 function visit(node){
  if(ts.isBinaryExpression(node)&&node.operatorToken.kind===ts.SyntaxKind.EqualsToken&&ts.isPropertyAccessExpression(node.left)&&node.left.expression.getText(file)==='window'&&node.left.name.text==='mount'&&(ts.isFunctionExpression(node.right)||ts.isArrowFunction(node.right))){
   const param=node.right.parameters[2];const bridge=param&&checker.getSymbolAtLocation(param.name);
   function scan(n){
    if(bridge&&ts.isCallExpression(n)&&ts.isPropertyAccessExpression(n.expression)&&n.expression.name.text==='read'&&checker.getSymbolAtLocation(n.expression.expression)===bridge){
     let arg=n.arguments[0];
     if(arg&&ts.isIdentifier(arg)){
      const decl=checker.getSymbolAtLocation(arg)?.valueDeclaration;
      arg=decl&&ts.isVariableDeclaration(decl)&&decl.parent.flags&ts.NodeFlags.Const?decl.initializer:undefined;
     }
     if(arg&&ts.isStringLiteralLike(arg))result.push({semantic_id:arg.text,line:file.getLineAndCharacterOfPosition(n.getStart(file)).line+1});
    }
    ts.forEachChild(n,scan);
   }
   scan(node.right.body);
  }
  ts.forEachChild(node,visit);
 }
 visit(file);return result;
}
module.exports={staticBridgeStateReads};
