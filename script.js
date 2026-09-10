const chat=document.getElementById("chat");
const messagesContainer=document.getElementById("messages");
const welcome=document.getElementById("welcome");
const typing=document.getElementById("typing");
const input=document.getElementById("messageInput");
const sendBtn=document.getElementById("sendBtn");
const newChatBtn=document.getElementById("newChatBtn");
const clearBtn=document.getElementById("clearBtn");

let sessionId=localStorage.getItem("edubot_session_id")||crypto.randomUUID();
localStorage.setItem("edubot_session_id",sessionId);

let history=JSON.parse(localStorage.getItem("edubot_history")||"[]");

function addMessageToUI(role,text){
  const row=document.createElement("div");
  row.className=`message-row ${role}`;
  const avatar=document.createElement("div");
  avatar.className="avatar";
  avatar.textContent=role==="user"?"👤":"🤖";
  const content=document.createElement("div");
  content.className="message-content";
  const name=document.createElement("div");
  name.className="message-name";
  name.textContent=role==="user"?"You":"EduBot AI";
  const bubble=document.createElement("div");
  bubble.className="message-bubble";
  bubble.textContent=text;
  content.append(name,bubble);
  row.append(avatar,content);
  messagesContainer.appendChild(row);
}

function saveMessage(role,text){
  history.push({role,text,time:new Date().toISOString()});
  if(history.length>30) history=history.slice(-30);
  localStorage.setItem("edubot_history",JSON.stringify(history));
}

function scrollBottom(){requestAnimationFrame(()=>chat.scrollTop=chat.scrollHeight)}

async function sendMessage(){
  const message=input.value.trim();
  if(!message)return;
  sendBtn.disabled=true;
  welcome.classList.add("hidden");
  addMessageToUI("user",message);
  saveMessage("user",message);
  input.value="";
  autoResize();
  typing.classList.remove("hidden");
  scrollBottom();

  try{
    const response=await fetch("/api/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message,session_id:sessionId,history})
    });
    const data=await response.json();
    if(!response.ok||!data.success) throw new Error(data.error||"Server error");
    if(data.session_id){
      sessionId=data.session_id;
      localStorage.setItem("edubot_session_id",sessionId);
    }
    addMessageToUI("assistant",data.answer);
    saveMessage("assistant",data.answer);
    await saveSession();
  }catch(error){
    console.error(error);
    addMessageToUI("assistant","⚠️ "+error.message);
  }finally{
    typing.classList.add("hidden");
    sendBtn.disabled=false;
    input.focus();
    scrollBottom();
  }
}

async function saveSession(){
  try{
    await fetch("/api/save-session",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({session_id:sessionId,messages:history})
    });
  }catch(error){console.log("Session save skipped:",error)}
}

async function clearChat(){
  if(!confirm("Clear this chat?"))return;
  try{
    await fetch("/api/delete-session",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({session_id:sessionId})
    });
  }catch(error){console.log(error)}
  history=[];
  localStorage.removeItem("edubot_history");
  sessionId=crypto.randomUUID();
  localStorage.setItem("edubot_session_id",sessionId);
  messagesContainer.innerHTML="";
  welcome.classList.remove("hidden");
}

function autoResize(){
  input.style.height="auto";
  input.style.height=Math.min(input.scrollHeight,150)+"px";
}

input.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){
    e.preventDefault();
    sendMessage();
  }
});
input.addEventListener("input",autoResize);
sendBtn.addEventListener("click",sendMessage);
clearBtn.addEventListener("click",clearChat);
newChatBtn.addEventListener("click",clearChat);

document.querySelectorAll(".quick-card,.tool-btn").forEach(button=>{
  button.addEventListener("click",()=>{
    input.value=button.dataset.prompt||"";
    autoResize();
    input.focus();
  });
});

if(history.length){
  welcome.classList.add("hidden");
  history.forEach(m=>addMessageToUI(m.role,m.text));
  scrollBottom();
}
