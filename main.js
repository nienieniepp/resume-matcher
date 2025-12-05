const API_BASE_URL = "https://resume-matcher-p2n1.onrender.com"; 

const uploadForm = document.getElementById("upload-form");
const resumeFileInput = document.getElementById("resume-file");
const uploadStatus = document.getElementById("upload-status");
const resumeInfo = document.getElementById("resume-info");

const jobTextarea = document.getElementById("job-description");
const matchButton = document.getElementById("match-button");
const matchStatus = document.getElementById("match-status");
const matchResult = document.getElementById("match-result");

let currentResumeId = null;

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = resumeFileInput.files[0];
  if (!file) {
    alert("请先选择一个 PDF 文件");
    return;
  }

  uploadStatus.textContent = "上传中...";
  resumeInfo.textContent = "";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch(`${API_BASE_URL}/upload-resume`, {
      method: "POST",
      body: formData,
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "上传失败");
    }

    const data = await resp.json();
    currentResumeId = data.resume.resume_id;
    uploadStatus.textContent = `解析完成，resume_id = ${currentResumeId}`;
    resumeInfo.textContent = JSON.stringify(data.resume, null, 2);
    matchButton.disabled = false;
  } catch (err) {
    console.error(err);
    uploadStatus.textContent = "上传或解析失败：" + err.message;
  }
});

matchButton.addEventListener("click", async () => {
  if (!currentResumeId) {
    alert("请先上传并解析简历");
    return;
  }
  const jd = jobTextarea.value.trim();
  if (!jd) {
    alert("请填写职位描述");
    return;
  }

  matchStatus.textContent = "匹配计算中...";
  matchResult.textContent = "";

  try {
    const resp = await fetch(`${API_BASE_URL}/match-job`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_id: currentResumeId,
        job_description: jd,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "匹配失败");
    }

    const data = await resp.json();
    matchStatus.textContent = `完成，综合匹配度：${(data.match_score.overall_score * 100).toFixed(1)}%`;
    matchResult.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    console.error(err);
    matchStatus.textContent = "匹配失败：" + err.message;
  }
});
