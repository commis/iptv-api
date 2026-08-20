// 核心计算函数
function calculatePrice() {
    // 获取输入框元素
    const initPriceInput = document.getElementById('initPrice');
    const buyAmountInput = document.getElementById('buyAmount');
    const profitPercentInput = document.getElementById('profitPercent');
    const lossPercentInput = document.getElementById('lossPercent');
    const buyPercentInput = document.getElementById('buyPercent');
    const sellPercentInput = document.getElementById('sellPercent');
    const resultSpan = document.getElementById('result');

    // 获取并转换输入值为数字
    const initPrice = parseFloat(initPriceInput.value);
    const buyAmount = parseInt(buyAmountInput.value);
    const profitPercent = parseFloat(profitPercentInput.value);
    const lossPercent = parseFloat(lossPercentInput.value);
    const buyPercent = parseFloat(buyPercentInput.value);
    const sellPercent = parseFloat(sellPercentInput.value);

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
    if (isNaN(buyPercent) || buyPercent < 0) {
        resultSpan.textContent = '请输入有效的买入（大于等于0）';
        resultSpan.style.color = '#f56c6c';
        return;
    }
    if (isNaN(sellPercent) || sellPercent < 0) {
        resultSpan.textContent = '请输入有效的卖出（大于等于0）';
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
    const buyPrice = initPrice * (1 - buyPercent / 100);
    const sellPrice = initPrice * (1 + sellPercent / 100);

    // 保留两位小数展示为横向表格，结果数据单元格内不带单位
    resultSpan.innerHTML =
        '<table class="result-table">' +
        '<thead>' +
        '<tr>' +
        '<th rowspan="2">初始价</th>' +
        '<th rowspan="2">成本价</th>' +
        '<th colspan="2">止盈止损</th>' +
        '<th colspan="2">做T操作</th>' +
        '</tr>' +
        '<tr>' +
        '<th>止盈</th>' +
        '<th>止损</th>' +
        '<th>买入</th>' +
        '<th>卖出</th>' +
        '</tr>' +
        '</thead>' +
        '<tbody>' +
        '<tr>' +
        '<td>' + initPrice.toFixed(2) + '</td>' +
        '<td>' + breakEvenPrice.toFixed(2) + '</td>' +
        '<td>' + profitPrice.toFixed(2) + '</td>' +
        '<td>' + lossPrice.toFixed(2) + '</td>' +
        '<td>' + buyPrice.toFixed(2) + '</td>' +
        '<td>' + sellPrice.toFixed(2) + '</td>' +
        '</tr>' +
        '</tbody></table>' +
        '<div class="result-warning">' +
        '<span>模式与纪律，决定收入；严守纪律，方能生存！</span>' +
        '</div>';
    resultSpan.style.color = '#409eff';
}