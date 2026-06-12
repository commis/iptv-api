function adjustValue(inputId, direction) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const step = parseFloat(input.step || 1) || 1;
    const min = input.min ? parseFloat(input.min) : null;
    const max = input.max ? parseFloat(input.max) : null;
    const current = parseFloat(input.value);
    const decimals = (step.toString().split('.')[1] || '').length;

    let newValue = isNaN(current) ? (direction > 0 ? step : 0) : current + direction * step;
    if (min !== null && !isNaN(min)) {
        newValue = Math.max(newValue, min);
    }
    if (max !== null && !isNaN(max)) {
        newValue = Math.min(newValue, max);
    }
    if (decimals > 0) {
        newValue = newValue.toFixed(decimals);
    }
    input.value = newValue;
}

// 核心计算函数
function calculatePrice() {
    // 获取输入框元素
    const initPriceInput = document.getElementById('initPrice');
    const buyAmountInput = document.getElementById('buyAmount');
    const profitPercentInput = document.getElementById('profitPercent');
    const lossPercentInput = document.getElementById('lossPercent');
    const resultSpan = document.getElementById('result');

    // 获取并转换输入值为数字
    const initPrice = parseFloat(initPriceInput.value);
    const buyAmount = parseInt(buyAmountInput.value);
    const profitPercent = parseFloat(profitPercentInput.value);
    const lossPercent = parseFloat(lossPercentInput.value);

    // 输入验证
    if (isNaN(initPrice) || initPrice <= 0) {
        resultSpan.textContent = '请输入有效的初始价格（大于0）';
        resultSpan.style.color = '#f56c6c';
        return;
    }
    if (isNaN(buyAmount) || buyAmount <= 0) {
        resultSpan.textContent = '请输入有效的买入量（大于0）';
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

    // 按照真实股票交易规则计算交易手续费
    // 买入手续费：0.1%（万分之十），最低5元
    const purchaseAmount = initPrice * buyAmount;
    const commissionRate = 0.001; // 0.1%
    const commission = Math.max(purchaseAmount * commissionRate, 5);
    const totalCost = purchaseAmount + commission;

    // 交易价应当基于总成本按每股分摊，确保包含手续费后不亏本
    const breakEvenPrice = totalCost / buyAmount;

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
        '<td>' + breakEvenPrice.toFixed(2) + '</td>' +
        '<td>' + profitPrice.toFixed(2) + '</td>' +
        '<td>' + lossPrice.toFixed(2) + '</td>' +
        '</tr>' +
        '</tbody></table>';
    resultSpan.style.color = '#409eff';
}