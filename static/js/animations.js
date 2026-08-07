// 动画效果管理器
class FloatingTextManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // 创建浮动文字容器
        if (!document.getElementById('floating-text-container')) {
            this.container = document.createElement('div');
            this.container.id = 'floating-text-container';
            this.container.className = 'floating-text-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('floating-text-container');
        }
    }

    // 显示属性变化浮动文字
    showAttributeChange(attr, value, x, y) {
        const text = document.createElement('div');
        text.className = 'floating-text attr-change';

        const prefix = value > 0 ? '+' : '';
        text.textContent = `${attr} ${prefix}${value}`;
        text.classList.add(value > 0 ? 'positive' : 'negative');

        // 设置初始位置
        text.style.left = `${x}px`;
        text.style.top = `${y}px`;

        this.container.appendChild(text);

        // 动画结束后移除
        setTimeout(() => {
            text.remove();
        }, 2000);
    }

    // 显示关键节点提示
    showPivotalNode(text, x, y) {
        const element = document.createElement('div');
        element.className = 'floating-text pivotal-node';
        element.textContent = text;

        element.style.left = `${x}px`;
        element.style.top = `${y}px`;

        this.container.appendChild(element);

        setTimeout(() => {
            element.remove();
        }, 3000);
    }

    // 显示成就解锁
    showAchievement(achievementName, x, y) {
        const element = document.createElement('div');
        element.className = 'floating-text achievement-unlock';
        element.innerHTML = `🏆 ${achievementName}`;

        element.style.left = `${x}px`;
        element.style.top = `${y}px`;

        this.container.appendChild(element);

        setTimeout(() => {
            element.remove();
        }, 3000);
    }
}

// 屏幕震动效果
function screenShake(intensity = 'medium') {
    const content = document.getElementById('content');
    if (!content) return;

    const intensityMap = {
        light: 'screen-shake-light',
        medium: 'screen-shake-medium',
        heavy: 'screen-shake-heavy'
    };

    const className = intensityMap[intensity] || intensityMap.medium;
    content.classList.add(className);

    setTimeout(() => {
        content.classList.remove(className);
    }, 500);
}

// 屏幕闪光效果
function screenFlash(color = 'white', duration = 300) {
    const flash = document.createElement('div');
    flash.className = 'screen-flash';
    flash.style.backgroundColor = color;
    flash.style.animationDuration = `${duration}ms`;

    document.body.appendChild(flash);

    setTimeout(() => {
        flash.remove();
    }, duration);
}

// 标记命运转折点
function markDestinyPivot() {
    const content = document.getElementById('content');
    if (!content) return;

    content.classList.add('destiny-pivot');

    setTimeout(() => {
        content.classList.remove('destiny-pivot');
    }, 2000);
}

// 选择按钮悬停效果增强
function enhanceChoiceButtons() {
    document.addEventListener('mouseover', (e) => {
        if (e.target.classList.contains('choice-btn')) {
            // 添加粒子效果
            createParticles(e.target);
        }
    });
}

// 创建粒子效果
function createParticles(element) {
    const rect = element.getBoundingClientRect();
    const particleCount = 5;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'choice-particle';

        const x = rect.left + Math.random() * rect.width;
        const y = rect.top + Math.random() * rect.height;

        particle.style.left = `${x}px`;
        particle.style.top = `${y}px`;

        document.body.appendChild(particle);

        setTimeout(() => {
            particle.remove();
        }, 1000);
    }
}

// 淡入淡出效果
function fadeTransition(callback) {
    const content = document.getElementById('content');
    if (!content) {
        callback();
        return;
    }

    content.classList.add('fade-out');

    setTimeout(() => {
        callback();
        content.classList.remove('fade-out');
        content.classList.add('fade-in');

        setTimeout(() => {
            content.classList.remove('fade-in');
        }, 300);
    }, 300);
}

// 章节过渡动画
function chapterTransition(chapterName) {
    const overlay = document.createElement('div');
    overlay.className = 'chapter-transition';
    overlay.innerHTML = `
        <div class="chapter-title">${chapterName}</div>
    `;

    document.body.appendChild(overlay);

    setTimeout(() => {
        overlay.classList.add('fade-out');
        setTimeout(() => {
            overlay.remove();
        }, 1000);
    }, 2000);
}

// 导出全局实例
window.floatingTextManager = new FloatingTextManager();
window.screenShake = screenShake;
window.screenFlash = screenFlash;
window.markDestinyPivot = markDestinyPivot;
window.fadeTransition = fadeTransition;
window.chapterTransition = chapterTransition;

// 初始化增强效果
document.addEventListener('DOMContentLoaded', () => {
    enhanceChoiceButtons();
});
