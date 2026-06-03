// ============================================================
// main.js - Xử lý hiển thị danh sách acc Free Fire
// Giao diện mới: neon green + pink + navy
// ============================================================

const BASE_URL = window.location.origin;

document.addEventListener("DOMContentLoaded", () => { loadAccounts(); });

async function loadAccounts() {
  const container = document.getElementById("account-list");
  const countEl = document.getElementById("account-count");
  showSkeleton(container);

  try {
    const res = await fetch(`${BASE_URL}/api/accounts`);
    const accounts = await res.json();

    if (accounts.length === 0) {
      container.innerHTML = `<div class="col-span-full text-center py-16"><p class="text-gray-500">Không có acc nào.</p></div>`;
      countEl.textContent = "";
      return;
    }

    countEl.textContent = `${accounts.length} acc`;
    container.innerHTML = accounts.map(acc => renderCard(acc)).join('');
  } catch (err) {
    container.innerHTML = `<div class="col-span-full text-center py-16">
      <p class="text-red-400 mb-4">Không thể tải dữ liệu</p>
      <button onclick="loadAccounts()" class="bg-neon-green text-black px-4 py-2 rounded-xl">Thử lại</button>
    </div>`;
  }
}

function renderCard(acc) {
  const priceFormatted = acc.price.toLocaleString("vi-VN");
  const isSold = acc.status === "Đã bán";
  const rankBadge = getRankBadge(acc.rank_level);

  return `
    <div class="bg-[#0d1117] rounded-2xl overflow-hidden border border-[#1e293b] card-hover flex flex-col ${isSold ? 'opacity-60' : ''}">
      <div class="relative aspect-[4/3] overflow-hidden">
        <img src="${acc.image_url || 'https://placehold.co/400x300/0d1117/1e293b?text=No+Image'}"
             alt="${acc.title}" class="w-full h-full object-cover ${isSold ? 'grayscale' : ''}"
             onerror="this.onerror=null; this.src='https://placehold.co/400x300/0d1117/1e293b?text=No+Image'">
        ${rankBadge}
        ${isSold ? '<span class="absolute top-3 right-3 bg-red-500/90 text-white text-xs font-bold px-3 py-1 rounded-full backdrop-blur-sm">ĐÃ BÁN</span>' : ''}
      </div>
      <div class="p-4 flex flex-col flex-1">
        <h4 class="text-white font-semibold text-sm leading-snug mb-3 min-h-[2.5rem]"
            style="display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
          ${escapeHtml(acc.title)}
        </h4>
        <p class="text-neon-green font-game text-lg font-bold mb-4 mt-auto">
          ${priceFormatted} <span class="text-xs font-body font-normal text-gray-500">VNĐ</span>
        </p>
        <a href="/acc/${acc.slug || acc.id}" target="_blank"
           class="block text-center ${isSold ? 'bg-gray-700 text-gray-400' : 'bg-neon-green hover:bg-green-400 text-black glow-green'} font-semibold py-2.5 rounded-xl transition-all text-sm">
          ${isSold ? 'Đã bán' : 'Xem chi tiết'}
        </a>
      </div>
    </div>
  `;
}

function getRankBadge(rankLevel) {
  if (!rankLevel) return "";
  const level = parseInt(rankLevel);
  let bg, text, label;
  if (!isNaN(level)) {
    if (level >= 70) { bg = "bg-cyan-500/20 border-cyan-400/50"; text = "text-cyan-300"; }
    else if (level >= 50) { bg = "bg-purple-500/20 border-purple-400/50"; text = "text-purple-300"; }
    else if (level >= 30) { bg = "bg-yellow-500/20 border-yellow-400/50"; text = "text-yellow-300"; }
    else { bg = "bg-gray-500/20 border-gray-400/50"; text = "text-gray-300"; }
    label = `Lv ${level}`;
  } else {
    bg = "bg-gray-500/20 border-gray-400/50"; text = "text-gray-300"; label = rankLevel;
  }
  return `<span class="absolute top-3 left-3 ${bg} ${text} border text-xs font-semibold px-2.5 py-1 rounded-full backdrop-blur-sm">${escapeHtml(label)}</span>`;
}

function showSkeleton(container) {
  let html = '';
  for (let i = 0; i < 8; i++) {
    html += `<div class="bg-[#0d1117] rounded-2xl overflow-hidden border border-[#1e293b]">
      <div class="aspect-[4/3] skeleton"></div>
      <div class="p-4 space-y-3"><div class="h-4 skeleton rounded w-3/4"></div><div class="h-4 skeleton rounded w-1/2"></div><div class="h-8 skeleton rounded-xl w-full mt-4"></div></div>
    </div>`;
  }
  container.innerHTML = html;
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
