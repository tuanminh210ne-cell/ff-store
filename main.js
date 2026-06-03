// ============================================================
// main.js - Xử lý hiển thị danh sách acc Free Fire
// Thuần JavaScript ES6+, không dùng framework
// ============================================================

// --- Auto-detect: dùng origin hiện tại (cùng domain với frontend) ---
const BASE_URL = window.location.origin;


// ============================================================
// Khởi tạo khi trang load xong
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  loadAccounts();
});


// ============================================================
// Gọi API lấy danh sách acc và render ra trang
// ============================================================
async function loadAccounts() {
  const container = document.getElementById("account-list");
  const countEl = document.getElementById("account-count");

  // Hiện skeleton loading trong khi chờ API
  showSkeleton(container);

  try {
    // Gọi API GET /api/accounts
    const response = await fetch(`${BASE_URL}/api/accounts`);

    // Nếu server trả lỗi
    if (!response.ok) {
      throw new Error(`Server lỗi: ${response.status}`);
    }

    // Parse JSON
    const accounts = await response.json();

    // Nếu không có acc nào
    if (accounts.length === 0) {
      container.innerHTML = `
        <div class="col-span-full text-center py-16">
          <p class="text-gray-500 text-lg">Không có acc nào đang bán.</p>
        </div>
      `;
      countEl.textContent = "";
      return;
    }

    // Cập nhật số lượng
    countEl.textContent = `${accounts.length} acc`;

    // Render từng card
    container.innerHTML = accounts.map(acc => renderCard(acc)).join("");

  } catch (error) {
    // Hiện thông báo lỗi đẹp
    console.error("Lỗi khi tải acc:", error);
    container.innerHTML = `
      <div class="col-span-full text-center py-16">
        <div class="inline-block bg-red-900/30 border border-red-800 rounded-xl p-8 max-w-md">
          <svg class="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/>
          </svg>
          <p class="text-red-400 font-semibold mb-2">Không thể tải dữ liệu</p>
          <p class="text-gray-500 text-sm">Vui lòng kiểm tra lại kết nối server hoặc thử lại sau.</p>
          <button onclick="loadAccounts()" class="mt-4 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm transition-colors">
            Thử lại
          </button>
        </div>
      </div>
    `;
    countEl.textContent = "";
  }
}


// ============================================================
// Render 1 card acc → trả về HTML string
// ============================================================
function renderCard(acc) {
  // Badge màu theo rank
  const rankBadge = getRankBadge(acc.rank_level);

  // Format giá tiền
  const priceFormatted = acc.price.toLocaleString("vi-VN");

  // Ảnh fallback nếu lỗi
  const imgOnError = "this.onerror=null; this.src='https://placehold.co/400x300/1a1a1a/666?text=No+Image'";

  return `
    <div class="bg-[#1a1a1a] rounded-xl overflow-hidden border border-gray-800 card-hover flex flex-col">
      <!-- Ảnh thumbnail -->
      <div class="relative aspect-[4/3] overflow-hidden">
        <img
          src="${acc.image_url || 'https://placehold.co/400x300/1a1a1a/666?text=No+Image'}"
          alt="${acc.title}"
          class="w-full h-full object-cover"
          onerror="${imgOnError}"
        />
        <!-- Badge rank góc trên trái -->
        ${rankBadge}
      </div>

      <!-- Nội dung -->
      <div class="p-4 flex flex-col flex-1">
        <!-- Tiêu đề: giới hạn 2 dòng -->
        <h4 class="text-white font-semibold text-sm leading-snug mb-3 line-clamp-2 min-h-[2.5rem]"
            style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
          ${escapeHtml(acc.title)}
        </h4>

        <!-- Giá tiền -->
        <p class="text-[#FF3333] font-game text-lg font-bold mb-4 mt-auto">
          ${priceFormatted} <span class="text-sm font-body font-normal text-gray-400">VNĐ</span>
        </p>

        <!-- Nút xem chi tiết -->
        <a href="/acc/${acc.slug || acc.id}" target="_blank"
           class="block text-center bg-[#FF3333] hover:bg-red-700 text-white font-semibold py-2.5 rounded-lg btn-glow transition-all text-sm">
          Xem chi tiết
        </a>
      </div>
    </div>
  `;
}


// ============================================================
// Tạo badge hiển thị Level
// ============================================================
function getRankBadge(rankLevel) {
  if (!rankLevel) return "";

  const level = parseInt(rankLevel);
  let bgClass, textClass, label;

  if (!isNaN(level)) {
    // Level là số
    if (level >= 70) {
      bgClass = "bg-cyan-500/20 border-cyan-400";
      textClass = "text-cyan-300";
    } else if (level >= 50) {
      bgClass = "bg-purple-500/20 border-purple-400";
      textClass = "text-purple-300";
    } else if (level >= 30) {
      bgClass = "bg-yellow-500/20 border-yellow-400";
      textClass = "text-yellow-300";
    } else {
      bgClass = "bg-gray-500/20 border-gray-400";
      textClass = "text-gray-300";
    }
    label = `Lv ${level}`;
  } else {
    // Level là text cũ (tương thích ngược)
    bgClass = "bg-gray-500/20 border-gray-400";
    textClass = "text-gray-300";
    label = rankLevel;
  }

  return `
    <span class="absolute top-3 left-3 ${bgClass} ${textClass} border text-xs font-semibold px-2.5 py-1 rounded-full backdrop-blur-sm">
      ${escapeHtml(label)}
    </span>
  `;
}


// ============================================================
// Hiện 8 skeleton card loading
// ============================================================
function showSkeleton(container) {
  let skeletons = "";

  for (let i = 0; i < 8; i++) {
    skeletons += `
      <div class="bg-[#1a1a1a] rounded-xl overflow-hidden border border-gray-800">
        <!-- Ảnh skeleton -->
        <div class="aspect-[4/3] skeleton"></div>
        <!-- Nội dung skeleton -->
        <div class="p-4 space-y-3">
          <div class="h-4 skeleton rounded w-3/4"></div>
          <div class="h-4 skeleton rounded w-1/2"></div>
          <div class="h-6 skeleton rounded w-1/3 mt-4"></div>
          <div class="h-10 skeleton rounded-lg w-full mt-4"></div>
        </div>
      </div>
    `;
  }

  container.innerHTML = skeletons;
}


// ============================================================
// Escape HTML để chống XSS
// ============================================================
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
