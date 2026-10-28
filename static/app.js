const $ = (id) => document.getElementById(id);
let enrollStream = null, scanStream = null, capturedSamples = [], toastTimer = null;

function toast(message) {
  const el = $("toast"); el.textContent = message; el.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}
function showMessage(id, text, error=false) {
  const el = $(id); el.textContent = text; el.classList.remove("hidden", "error");
  if (error) el.classList.add("error");
}
function hideMessage(id) { $(id).classList.add("hidden"); }
async function api(url, options={}) {
  const response = await fetch(url, {headers: {"Content-Type":"application/json"}, ...options});
  const data = await response.json().catch(()=>({error:"Unexpected server response."}));
  if (!response.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}
function switchView(name) {
  document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id===`view-${name}`));
  document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===name));
  const label = ({overview:"Overview",students:"Students",enroll:"Face enrollment",scan:"Live scan",attendance:"Attendance",testing:"Testing dashboard"})[name] || "Overview";
  $("crumb").textContent=label;
  if(name==="students") loadStudents();
  if(name==="enroll") loadStudentOptions();
  if(name==="attendance") loadAttendance();
  if(name==="testing") resetTestingHint();
  if(name==="overview") loadOverview();
  window.scrollTo({top:0,behavior:"smooth"});
}
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>switchView(b.dataset.view)));
document.querySelectorAll("[data-goto]").forEach(b=>b.addEventListener("click",()=>switchView(b.dataset.goto)));

function initials(name){return (name||"?").trim().split(/\s+/).slice(0,2).map(s=>s[0]).join("").toUpperCase()}
function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}

async function loadOverview(){
  try{
    const d=await api("/api/status");
    $("statStudents").textContent=d.students;$("statPresent").textContent=d.today_present;$("statRecords").textContent=d.total_records;
    $("statEngine").textContent=d.model_available?"Available":"Unavailable";
    $("topDate").textContent=d.today;
    $("recentList").innerHTML=d.recent.length?d.recent.map(r=>`<div class="recent-item"><div class="student-avatar">${escapeHtml(initials(r.name))}</div><div class="recent-person"><strong>${escapeHtml(r.name)}</strong><span>Roll no. ${escapeHtml(r.roll_no)} · ${escapeHtml(r.attendance_time)}</span></div><span class="present-badge">${escapeHtml(r.status)}</span></div>`).join(""):'<div class="empty-state">No attendance records yet.<br>Start a scan to see activity here.</div>';
  }catch(e){toast(e.message)}
}

async function loadStudents(){
  try{
    const list=await api("/api/students"); const q=($("studentSearch").value||"").toLowerCase();
    const filtered=list.filter(s=>s.name.toLowerCase().includes(q)||s.roll_no.toLowerCase().includes(q));
    $("studentCount").textContent=`${filtered.length} student${filtered.length===1?"":"s"}`;
    $("studentsTable").innerHTML=filtered.map(s=>`<tr><td><div class="student-cell"><div class="student-avatar">${escapeHtml(initials(s.name))}</div><div><strong>${escapeHtml(s.name)}</strong><small>${escapeHtml(s.year||"Student")}</small></div></div></td><td><span class="roll-pill">${escapeHtml(s.roll_no)}</span></td><td>${escapeHtml(s.department)}</td><td><span class="sample-badge">Enrolled samples</span></td><td>${s.attendance_count}</td><td><button class="row-action" data-delete="${s.id}" data-name="${escapeHtml(s.name)}">Remove</button></td></tr>`).join("");
    $("studentsEmpty").style.display=filtered.length?"none":"block";
    $("studentsTable").querySelectorAll("[data-delete]").forEach(b=>b.addEventListener("click",async()=>{
      if(!confirm(`Remove ${b.dataset.name}? This also deletes their face samples and attendance records.`))return;
      try{await api(`/api/students/${b.dataset.delete}`,{method:"DELETE"});toast("Student removed.");loadStudents();loadOverview();}catch(e){toast(e.message)}
    }));
  }catch(e){toast(e.message)}
}
$("studentSearch").addEventListener("input",loadStudents);
function openModal(){ $("studentModal").classList.remove("hidden"); $("studentName").focus()}
function closeModal(){ $("studentModal").classList.add("hidden"); $("studentForm").reset();hideMessage("studentFormMessage")}
$("openStudentForm").addEventListener("click",openModal);
$("closeStudentModal").addEventListener("click",closeModal);
$("cancelStudent").addEventListener("click",closeModal);
$("studentModal").addEventListener("click",e=>{if(e.target===$("studentModal"))closeModal()});
$("studentForm").addEventListener("submit",async e=>{
  e.preventDefault();hideMessage("studentFormMessage");
  try{
    const d=await api("/api/students",{method:"POST",body:JSON.stringify({name:$("studentName").value,roll_no:$("studentRoll").value,department:$("studentDept").value,year:$("studentYear").value})});
    closeModal();toast(d.message);loadStudents();loadOverview();loadStudentOptions();
  }catch(err){showMessage("studentFormMessage",err.message,true)}
});

async function loadStudentOptions(){
  try{
    const list=await api("/api/students");const select=$("enrollStudent");const old=select.value;
    select.innerHTML='<option value="">Select a student…</option>'+list.map(s=>`<option value="${s.id}">${escapeHtml(s.name)} — ${escapeHtml(s.roll_no)}</option>`).join("");
    if(list.some(s=>String(s.id)===old))select.value=old;
  }catch(e){toast(e.message)}
}
function stopStream(which){
  const key=which==="enroll"?"enrollStream":"scanStream";
  if(window[key]){window[key].getTracks().forEach(t=>t.stop());window[key]=null}
}
async function startCamera(which){
  const video=$(which==="enroll"?"enrollVideo":"scanVideo"), placeholder=$(which==="enroll"?"enrollPlaceholder":"scanPlaceholder");
  try{
    stopStream(which);
    const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"user",width:{ideal:1280},height:{ideal:720}},audio:false});
    if(which==="enroll")enrollStream=stream;else scanStream=stream;
    video.srcObject=stream;await video.play();placeholder.classList.add("hidden");
    if(which==="enroll"){$("captureSample").disabled=false;toast("Camera enabled. Capture face samples.");}
    else{$("scanNow").disabled=false;$("scanState").textContent="READY";toast("Camera enabled. Ready to scan.");}
  }catch(e){toast("Camera access failed. Allow camera permission and try again.");}
}
$("startEnrollCamera").addEventListener("click",()=>startCamera("enroll"));
$("startScanCamera").addEventListener("click",()=>startCamera("scan"));
function captureFrame(videoId,canvasId){
  const video=$(videoId),canvas=$(canvasId);
  if(!video.videoWidth||!video.videoHeight)throw new Error("Camera is not ready yet.");
  canvas.width=video.videoWidth;canvas.height=video.videoHeight;
  const ctx=canvas.getContext("2d");ctx.save();ctx.translate(canvas.width,0);ctx.scale(-1,1);ctx.drawImage(video,0,0,canvas.width,canvas.height);ctx.restore();
  return canvas.toDataURL("image/jpeg",.86);
}
function updateSamples(){
  $("sampleCounter").textContent=`${capturedSamples.length} samples`;
  $("sampleCountSide").textContent=`${capturedSamples.length} / 8`;
  $("sampleProgress").style.width=`${Math.min(capturedSamples.length/8*100,100)}%`;
  $("saveEnrollment").disabled=capturedSamples.length<3||!$("enrollStudent").value;
  $("sampleStrip").innerHTML=capturedSamples.length?capturedSamples.map((s,i)=>`<img class="sample-thumb" alt="Sample ${i+1}" src="${s}">`).join(""):'<span class="sample-hint">Your captured samples will appear here.</span>';
}
$("enrollStudent").addEventListener("change",()=>{updateSamples();hideMessage("enrollMessage")});
$("captureSample").addEventListener("click",()=>{
  if(!$("enrollStudent").value){showMessage("enrollMessage","Select a student before capturing samples.",true);return}
  try{capturedSamples.push(captureFrame("enrollVideo","enrollCanvas"));updateSamples();hideMessage("enrollMessage");}
  catch(e){showMessage("enrollMessage",e.message,true)}
});
$("saveEnrollment").addEventListener("click",async()=>{
  if(capturedSamples.length<3)return;
  $("saveEnrollment").disabled=true;$("saveEnrollment").textContent="Training model…";hideMessage("enrollMessage");
  try{
    const d=await api("/api/enroll",{method:"POST",body:JSON.stringify({student_id:$("enrollStudent").value,images:capturedSamples})});
    showMessage("enrollMessage",d.message+(d.errors?.length?` ${d.errors.length} sample(s) had no detectable face.`:""));
    capturedSamples=[];updateSamples();loadOverview();toast("Enrollment saved.");
  }catch(e){showMessage("enrollMessage",e.message,true)}
  finally{$("saveEnrollment").textContent="Save & train model";updateSamples()}
});
$("scanNow").addEventListener("click",async()=>{
  $("scanNow").disabled=true;$("scanNow").textContent="Scanning…";$("scanState").textContent="SCANNING";hideMessage("scanMessage");
  try{
    const image=captureFrame("scanVideo","scanCanvas");const d=await api("/api/scan",{method:"POST",body:JSON.stringify({image})});
    if(d.recognized){
      $("resultIllustration").textContent=d.duplicate?"✓":"✳";$("resultIllustration").style.background=d.duplicate?"#f3ebdc":"#e5ece0";
      $("resultTitle").textContent=d.duplicate?"Already marked today":"Student recognized";
      $("resultDescription").textContent=d.message;
      $("resultDetails").classList.remove("hidden");$("resultName").textContent=d.name;$("resultRoll").textContent=d.roll_no;$("resultTime").textContent=d.time;$("resultConfidence").textContent=d.confidence;
      $("scanState").textContent="MATCH";
      showMessage("scanMessage",d.message);
      loadOverview();
    }else{
      $("resultIllustration").textContent="◎";$("resultIllustration").style.background="#f5e7e2";$("resultTitle").textContent="No match found";$("resultDescription").textContent=d.message;$("resultDetails").classList.add("hidden");$("scanState").textContent="NO MATCH";showMessage("scanMessage",d.message,true);
    }
  }catch(e){$("resultTitle").textContent="Scan unavailable";$("resultDescription").textContent=e.message;$("resultDetails").classList.add("hidden");showMessage("scanMessage",e.message,true);$("scanState").textContent="ERROR"}
  finally{$("scanNow").disabled=false;$("scanNow").innerHTML='Scan face <span>⌾</span>'}
});
function localDateString(d=new Date()){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`}
$("attendanceDate").value=localDateString();
async function loadAttendance(){
  const selected=$("attendanceDate").value||localDateString();
  try{
    const rows=await api(`/api/attendance?date=${encodeURIComponent(selected)}`);
    $("attendanceTable").innerHTML=rows.map(r=>`<tr><td><div class="student-cell"><div class="student-avatar">${escapeHtml(initials(r.name))}</div><div><strong>${escapeHtml(r.name)}</strong><small>${escapeHtml(r.department)}</small></div></div></td><td><span class="roll-pill">${escapeHtml(r.roll_no)}</span></td><td>${escapeHtml(r.attendance_date)}</td><td>${escapeHtml(r.attendance_time)}</td><td><span class="present-badge">${escapeHtml(r.status)}</span></td></tr>`).join("");
    $("attendanceEmpty").style.display=rows.length?"none":"block";$("attendanceTotal").textContent=`${rows.length} present`;
  }catch(e){toast(e.message)}
}
$("attendanceDate").addEventListener("change",loadAttendance);
$("exportCsv").addEventListener("click",()=>{const d=$("attendanceDate").value||localDateString();window.location.href=`/api/attendance/export?date=${encodeURIComponent(d)}`});
loadOverview();

function resetTestingHint(){
  // Results remain visible after navigation until the next run.
}
$("runTestsButton").addEventListener("click", async()=>{
  const button=$("runTestsButton");button.disabled=true;button.textContent="Running tests…";
  $("testRunTitle").textContent="Tests are running";$("testRunBadge").textContent="Running";$("testRunBadge").className="test-badge running";
  $("testRunHint").textContent="Pytest is executing the project's automated test suite. This may take a few seconds.";
  $("testResultsBody").innerHTML="";$("testEmpty").style.display="none";$("testOutput").textContent="Running pytest…";
  try{
    const d=await api("/api/tests/run",{method:"POST",body:"{}"});
    const c=d.counts||{};$("testTotal").textContent=d.total??0;$("testPassed").textContent=c.passed??0;$("testFailed").textContent=(c.failed||0)+(c.error||0);$("testSkipped").textContent=c.skipped??0;
    $("testRunTitle").textContent=d.success?"Automated test run completed":"Test run completed with issues";
    $("testRunBadge").textContent=d.success?"All passed":"Review results";$("testRunBadge").className="test-badge "+(d.success?"passed":"failed");
    $("testRunHint").textContent=`Executed ${d.total} test case(s). These statuses come from the actual pytest run, not a simulated result.`;
    $("testResultsBody").innerHTML=(d.cases||[]).map(t=>`<tr><td><div class="test-case-name">${escapeHtml(t.name)}<small>${escapeHtml(t.id)}</small></div></td><td><span class="test-badge ${t.status==='passed'?'passed':t.status==='skipped'?'neutral':'failed'}">${escapeHtml(t.status.toUpperCase())}</span></td></tr>`).join("");
    $("testEmpty").style.display=d.cases&&d.cases.length?"none":"block";$("testOutput").textContent=d.output||"pytest returned no output.";
    toast(d.success?`Tests complete: ${c.passed||0} passed.`:"Tests finished. Review failed cases.");
  }catch(e){$("testRunTitle").textContent="Could not run tests";$("testRunBadge").textContent="Error";$("testRunBadge").className="test-badge failed";$("testRunHint").textContent=e.message;$("testOutput").textContent=e.message;toast(e.message)}
  finally{button.disabled=false;button.innerHTML='▶ Run automated tests'}
});
