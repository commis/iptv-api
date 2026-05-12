// 核心计算函数
function calculatePrice() {
    // 获取输入框元素
    const initPriceInput = document.getElementById('initPrice');
    const feeInput = document.getElementById('fee');
    const resultSpan = document.getElementById('result');

    // 获取并转换输入值为数字
    const initPrice = parseFloat(initPriceInput.value);
    const fee = parseFloat(feeInput.value);

    // 输入验证
    if (isNaN(initPrice) || initPrice <= 0) {
        resultSpan.textContent = '请输入有效的初始价格（大于0）';
        resultSpan.style.color = '#f56c6c';
        return;
    }
    if (isNaN(fee) || fee < 0) {
        resultSpan.textContent = '请输入有效的交易费用（大于等于0）';
        resultSpan.style.color = '#f56c6c';
        return;
    }

    // 执行计算公式：初始价格*(1 + (交易费/初始价格)/100)
    const result = initPrice * (1 + (fee / initPrice) / 100);

    // 保留两位小数展示（符合货币格式）
    resultSpan.textContent = result.toFixed(2) + ' 元';
    resultSpan.style.color = '#409eff';
}