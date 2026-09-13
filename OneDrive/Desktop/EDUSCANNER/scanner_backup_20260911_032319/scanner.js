let stream=null,lastResults=[];
const camera=document.getElementById("camera"),canvas=document.getElementById("canvas"),msg=document.getElementById("scan-message");
const results=document.getElementById("results"),saveBtn=document.getElementById("save-result");
const selectedCard=()=>document.getElementById("card_id").value;

async function startCamera(){
 try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"}},audio:false});
 camera.srcObject=stream;msg.textContent="Câmera ativa. Deixe o cartão inteiro visível e capture.";
 }catch(e){msg.textContent="Não foi possível abrir a câmera. Use 'Enviar foto'."}
}
async function analyzeBlob(blob){
 const fd=new FormData();fd.append("card_id",selectedCard());fd.append("image",blob,"card.jpg");
 msg.textContent="Lendo as marcações vermelhas...";
 const r=await fetch("/api/scanner/analyze",{method:"POST",body:fd}),d=await r.json();
 if(!d.ok){msg.textContent=d.message||"Erro na leitura.";return}
 lastResults=d.questions;document.getElementById("result-count").textContent=`${d.question_count} questões`;
 results.innerHTML=d.questions.map(q=>{
   const label=q.status==="MULT"?"MÚLT":q.status==="BLANK"?"—":q.answer;
   const cls=q.status==="OK"?"":"bad";
   return `<div class="result-item ${cls}"><div class="q">Q${q.number}</div><div class="ans">${label}</div></div>`;
 }).join("");
 msg.textContent=d.message;saveBtn.disabled=false;
}
document.getElementById("start-camera").onclick=startCamera;
document.getElementById("capture").onclick=()=>{
 if(!camera.srcObject){msg.textContent="Abra a câmera primeiro ou envie uma foto.";return}
 const w=camera.videoWidth,h=camera.videoHeight;if(!w||!h){msg.textContent="A câmera ainda não está pronta.";return}
 canvas.width=w;canvas.height=h;canvas.getContext("2d").drawImage(camera,0,0,w,h);canvas.toBlob(analyzeBlob,"image/jpeg",.92);
};
document.getElementById("upload").onchange=e=>{const f=e.target.files[0];if(f)analyzeBlob(f)};
saveBtn.onclick=async()=>{
 if(!lastResults.length)return;
 const fd=new FormData();fd.append("card_id",selectedCard());fd.append("classroom_id",document.getElementById("classroom_id").value);
 fd.append("student_id",document.getElementById("student_id").value);fd.append("answers_json",JSON.stringify(lastResults));
 const r=await fetch("/api/scanner/save",{method:"POST",body:fd}),d=await r.json();
 msg.textContent=d.ok?`Correção salva: ${d.correct} acertos, ${d.wrong} erros e ${d.blank} em branco.`:d.message;
};
