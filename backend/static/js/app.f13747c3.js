// 核心计算函数
function calculatePrice() {
    // 获取输入框元素
    const initPriceInput = document.getElementById('initPrice');
    const feeInput = document.getElementById('fee');
    const profitPercentInput = document.getElementById('profitPercent');
    const lossPercentInput = document.getElementById('lossPercent');
    const resultSpan = document.getElementById('result');

    // 获取并转换输入值为数字
    const initPrice = parseFloat(initPriceInput.value);
    const fee = parseFloat(feeInput.value);
    const profitPercent = parseFloat(profitPercentInput.value);
    const lossPercent = parseFloat(lossPercentInput.value);

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
    if (isNaN(profitPercent) || profitPercent < 0) {
        resultSpan.textContent = '请输入有效的止盈（大于等于0）';
        resultSpan.style.color = '#f56c6c';
        return;
    }
    if (isNaN(lossPercent) || lossPercent < 0) {
        resultSpan.textContent = '请输入有效的止损（大于等于0）';
        resultSpan.style.color = '#f56c6c';
        return;
    }

    // 按交易费用计算后的价格（保留现有逻辑）
    const feeResult = initPrice * (1 + (fee / initPrice) / 100);
    // 根据初始价格自动计算止盈、止损价格
    const profitPrice = initPrice * (1 + profitPercent / 100);
    const lossPrice = initPrice * (1 - lossPercent / 100);

    // 保留两位小数展示为横向表格，结果数据单元格内不带单位
    resultSpan.innerHTML =
        '<table class="result-table">' +
        '<thead><tr><th>初始价</th><th>交易价</th><th>止盈</th><th>止损</th></tr></thead>' +
        '<tbody>' +
        '<tr>' +
        '<td>' + initPrice.toFixed(2) + '</td>' +
        '<td>' + feeResult.toFixed(2) + '</td>' +
        '<td>' + profitPrice.toFixed(2) + '</td>' +
        '<td>' + lossPrice.toFixed(2) + '</td>' +
        '</tr>' +
        '</tbody></table>';
    resultSpan.style.color = '#409eff';
}