// 全局变量
let currentSort = {
    column: null,
    direction: 'asc'
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化标签页
    const triggerTabList = [].slice.call(document.querySelectorAll('#tradeTabs button'));
    triggerTabList.forEach(function(triggerEl) {
        const tabTrigger = new bootstrap.Tab(triggerEl);
        triggerEl.addEventListener('click', function(event) {
            event.preventDefault();
            tabTrigger.show();
        });
    });

    // 加载Steam库存数据
    loadSteamInventory();

    // 加载初始数据
    loadData();

    // 添加事件监听器
    addEventListeners();
});

// 添加事件监听器
function addEventListeners() {
    // 添加排序事件监听器
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            sortTable(column);
        });
    });

    // 添加刷新余额的功能
    document.querySelectorAll('.refresh-balance').forEach(button => {
        button.addEventListener('click', async function() {
            const platform = this.dataset.platform;
            await updateBalance(platform, this);
        });
    });
}

// 加载数据
async function loadData() {
    try {
        console.log('开始加载数据...');
        const response = await fetch('/api/data');
        const data = await response.json();
        console.log('获取到的数据:', data);
        
        updateDashboard(data);
        updateTables(data);
        
        console.log('数据加载完成');
    } catch (error) {
        console.error('加载数据失败:', error);
    }
}

// 更新仪表板数据
function updateDashboard(data) {
    // 更新统计数据
    document.getElementById('totalInvestment').textContent = `¥${data.total_investment.toFixed(2)}`;
    document.getElementById('currentValue').textContent = `¥${data.inventory_value.toFixed(2)}`;
    document.getElementById('totalValue').textContent = `¥${data.total_value.toFixed(2)}`;
    document.getElementById('totalProfit').textContent = `¥${data.total_profit.toFixed(2)}`;
    document.getElementById('profitRatio').textContent = `利润率: ${data.profit_ratio.toFixed(2)}%`;
    
    // 更新账户余额
    document.getElementById('totalBalance').textContent = `¥${data.total_balance.toFixed(2)}`;
    document.getElementById('buffBalance').textContent = `¥${data.buff_balance.toFixed(2)}`;
    document.getElementById('youpinBalance').textContent = `¥${data.youpin_balance.toFixed(2)}`;
    document.getElementById('igxeBalance').textContent = `¥${data.igxe_balance.toFixed(2)}`;
    document.getElementById('c5Balance').textContent = `¥${data.c5_balance.toFixed(2)}`;
    
    // 更新BUFF统计数据
    document.getElementById('buffTotalBuy').textContent = `¥${data.buff_total_buy.toFixed(2)}`;
    document.getElementById('buffTotalSale').textContent = `¥${data.buff_total_sale.toFixed(2)}`;
    document.getElementById('buffNetProfit').textContent = `¥${data.buff_net_profit.toFixed(2)}`;
}

// 更新表格
function updateTables(data) {
    updateHoldingsTable(data.holdings);
    updateCompletedTradesTable(data.completed_trades);
}

// 更新持有记录表格
function updateHoldingsTable(holdings) {
    const holdingsTableBody = document.getElementById('holdingsTableBody');
    holdingsTableBody.innerHTML = '';
    if (holdings && holdings.length > 0) {
        holdings.forEach(trade => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><a href="${trade.item_url || '#'}" target="_blank" class="text-decoration-none">${trade.item_name}</a></td>
                <td>${trade.quantity}</td>
                <td>¥${trade.unit_price.toFixed(2)}</td>
                <td>¥${trade.total_price.toFixed(2)}</td>
                <td>${trade.purchase_date}</td>
                <td>${trade.platform}</td>
            `;
            holdingsTableBody.appendChild(row);
        });
    } else {
        holdingsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">暂无持有记录</td></tr>';
    }
}

// 更新成交记录表格
function updateCompletedTradesTable(completed_trades) {
    const completedTableBody = document.getElementById('completedTableBody');
    completedTableBody.innerHTML = '';
    
    if (completed_trades && completed_trades.length > 0) {
        // 检查数据结构
        console.log('检查第一条记录的数据结构:', completed_trades[0]);
        
        // 使用Map存储买入记录，key为物品名称
        const buyMap = new Map();
        
        // 每条记录都作为买入记录处理
        completed_trades.forEach(trade => {
            const itemName = trade.item_name;
            if (!buyMap.has(itemName)) {
                buyMap.set(itemName, []);
            }
            // 存储买入信息，计算单个物品的价格
            buyMap.get(itemName).push({
                item_name: trade.item_name,
                unit_price: trade.total_price / trade.quantity, // 计算真实的单价
                total_price: trade.total_price,
                purchase_date: trade.purchase_date,
                quantity: trade.quantity
            });
        });
        
        console.log('买入记录Map:', Object.fromEntries(buyMap));
        
        // 处理卖出记录
        const processedItems = new Map();
        
        // 只处理有sale_date的记录作为卖出记录
        completed_trades.filter(trade => trade.sale_date).forEach(trade => {
            const itemName = trade.item_name;
            
            // 判断是否为可批量交易的物品
            const isBulkItem = trade.item_name.includes('印花') || 
                             trade.item_name.includes('武器箱') || 
                             trade.item_name.includes('封装的涂鸦');
            
            if (processedItems.has(itemName)) {
                if (isBulkItem) {
                    const existingItem = processedItems.get(itemName);
                    existingItem.quantity += trade.quantity;
                    existingItem.sale_price += trade.sale_price;
                    if (existingItem.total_price !== '-') {
                        existingItem.total_price += trade.total_price;
                    }
                }
                return;
            }
            
            // 查找对应的买入记录
            const matchingBuyRecords = buyMap.get(itemName) || [];
            console.log(`查找 ${itemName} 的买入记录:`, matchingBuyRecords);
            
            // 使用相同记录的买入信息
            const buyRecord = matchingBuyRecords.find(record => 
                record.purchase_date === trade.purchase_date
            ) || matchingBuyRecords[0];
            
            const quantity = isBulkItem ? trade.quantity : 1;
            
            processedItems.set(itemName, {
                ...trade,
                quantity: quantity,
                sale_price: trade.sale_price,
                unit_price: buyRecord ? buyRecord.unit_price : '-',
                total_price: buyRecord ? buyRecord.unit_price * quantity : '-', // 根据数量计算总价
                purchase_date: buyRecord ? buyRecord.purchase_date : '-'
            });
        });
        
        // 显示处理后的物品
        processedItems.forEach(trade => {
            const profit = trade.total_price !== '-' ? trade.sale_price - trade.total_price : '-';
            const profitClass = profit === '-' ? '' : (profit >= 0 ? 'text-success' : 'text-danger');
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><a href="${trade.item_url || '#'}" target="_blank" class="text-decoration-none">${trade.item_name}</a></td>
                <td>${trade.quantity}</td>
                <td>${trade.unit_price === '-' ? '-' : `¥${trade.unit_price.toFixed(2)}`}</td>
                <td>${trade.total_price === '-' ? '-' : `¥${trade.total_price.toFixed(2)}`}</td>
                <td>¥${trade.sale_price.toFixed(2)}</td>
                <td class="${profitClass}">${profit === '-' ? '-' : `¥${profit.toFixed(2)}`}</td>
                <td>${trade.purchase_date}</td>
                <td>${trade.sale_date}</td>
                <td>${trade.platform}</td>
            `;
            completedTableBody.appendChild(row);
        });
    } else {
        completedTableBody.innerHTML = '<tr><td colspan="9" class="text-center">暂无成交记录</td></tr>';
    }
}

// 表格排序
function sortTable(column) {
    const table = document.querySelector('.tab-pane.active table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // 更新排序状态
    const header = document.querySelector(`[data-sort="${column}"]`);
    const isAsc = header.classList.contains('asc');
    
    // 更新所有表头的排序状态
    document.querySelectorAll('.sortable').forEach(h => {
        h.classList.remove('asc', 'desc');
    });
    
    // 设置当前表头的排序状态
    header.classList.add(isAsc ? 'desc' : 'asc');
    
    // 排序行
    rows.sort((a, b) => {
        const aValue = a.querySelector(`td:nth-child(${getColumnIndex(column)})`).textContent;
        const bValue = b.querySelector(`td:nth-child(${getColumnIndex(column)})`).textContent;
        
        // 处理数字
        if (column.includes('price') || column.includes('quantity')) {
            const aNum = parseFloat(aValue.replace('¥', '')) || 0;
            const bNum = parseFloat(bValue.replace('¥', '')) || 0;
            return isAsc ? bNum - aNum : aNum - bNum;
        }
        
        // 处理日期
        if (column.includes('date')) {
            const aDate = new Date(aValue);
            const bDate = new Date(bValue);
            return isAsc ? bDate - aDate : aDate - bDate;
        }
        
        // 处理文本
        return isAsc ? bValue.localeCompare(aValue) : aValue.localeCompare(bValue);
    });
    
    // 重新添加排序后的行
    rows.forEach(row => tbody.appendChild(row));
}

// 获取列索引
function getColumnIndex(column) {
    const columnMap = {
        'item_name': 1,
        'quantity': 2,
        'unit_price': 3,
        'total_price': 4,
        'sale_price': 5,
        'profit': 6,
        'purchase_date': 7,
        'sale_date': 8,
        'platform': 9
    };
    return columnMap[column] || 1;
}

// 更新余额
async function updateBalance(platform, button) {
    const icon = button.querySelector('i');
    button.disabled = true;
    icon.classList.add('fa-spin');
    
    try {
        console.log(`开始更新${platform}余额...`);
        const response = await fetch(`/api/update_balance?platform=${platform}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        console.log('收到服务器响应数据:', data);
        
        if (!response.ok) {
            throw new Error(data.error || '更新失败');
        }
        
        // 检查当前平台的余额状态
        const platformMap = {
            'buff': 'BUFF',
            'youpin': '悠悠有品',
            'igxe': 'IGXE',
            'c5': 'C5'
        };
        
        const currentPlatform = platformMap[platform];
        const updateStatus = data.update_status[`${platform}_balance`];
        
        console.log(`检查${currentPlatform}余额更新状态:`, updateStatus);
        
        // 更新显示的余额
        updateBalanceDisplay(data);
        
        if (!updateStatus) {
            console.log(`${currentPlatform}余额更新失败`);
            showToast(`${currentPlatform}余额更新失败，保持原有余额`, 'error');
        } else {
            console.log(`${currentPlatform}余额更新成功`);
            showToast(`${currentPlatform}余额更新成功`, 'success');
        }
    } catch (error) {
        console.error('更新余额失败:', error);
        showToast('更新失败: ' + error.message, 'error');
    } finally {
        button.disabled = false;
        icon.classList.remove('fa-spin');
    }
}

// 更新余额显示
function updateBalanceDisplay(data) {
    console.log('开始更新余额显示');
    console.log('当前数据:', data);
    
    if (data.buff_balance !== undefined && data.buff_balance !== null) {
        console.log('更新BUFF余额显示:', data.buff_balance);
        document.getElementById('buffBalance').textContent = `¥${data.buff_balance.toFixed(2)}`;
    } else {
        console.log('BUFF余额未更新');
    }
    
    if (data.youpin_balance !== undefined && data.youpin_balance !== null) {
        console.log('更新悠悠有品余额显示:', data.youpin_balance);
        document.getElementById('youpinBalance').textContent = `¥${data.youpin_balance.toFixed(2)}`;
    } else {
        console.log('悠悠有品余额未更新');
    }
    
    if (data.igxe_balance !== undefined && data.igxe_balance !== null) {
        console.log('更新IGXE余额显示:', data.igxe_balance);
        document.getElementById('igxeBalance').textContent = `¥${data.igxe_balance.toFixed(2)}`;
    } else {
        console.log('IGXE余额未更新');
    }
    
    if (data.c5_balance !== undefined && data.c5_balance !== null) {
        console.log('更新C5余额显示:', data.c5_balance);
        document.getElementById('c5Balance').textContent = `¥${data.c5_balance.toFixed(2)}`;
    } else {
        console.log('C5余额未更新');
    }
    
    if (data.total_balance !== undefined && data.total_balance !== null) {
        console.log('更新总余额显示:', data.total_balance);
        document.getElementById('totalBalance').textContent = `¥${data.total_balance.toFixed(2)}`;
    } else {
        console.log('总余额未更新');
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    console.log('显示提示消息:', message, '类型:', type);
    
    // 创建toast容器（如果不存在）
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.position = 'fixed';
        toastContainer.style.top = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // 创建toast元素
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // 设置toast内容
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // 添加到容器
    toastContainer.appendChild(toast);
    
    // 初始化Bootstrap Toast
    const bsToast = new bootstrap.Toast(toast, {
        animation: true,
        autohide: true,
        delay: 3000
    });
    
    // 显示toast
    bsToast.show();
    
    // 监听隐藏事件，移除元素
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// 切换编辑模式
function toggleEdit(elementId) {
    const displayElement = document.getElementById(`${elementId}Display`);
    const editElement = document.getElementById(`${elementId}Edit`);
    const currentValue = document.getElementById(elementId).textContent.replace('¥', '');
    const input = document.getElementById(`${elementId}Input`);
    const editButton = document.querySelector(`button[onclick="toggleEdit('${elementId}')"]`);
    
    if (editElement.classList.contains('d-none')) {
        // 显示编辑表单
        displayElement.classList.add('d-none');
        editElement.classList.remove('d-none');
        input.value = currentValue;
        input.focus(); // 自动聚焦到输入框
        // 隐藏编辑按钮
        editButton.classList.add('d-none');
    } else {
        // 隐藏编辑表单
        displayElement.classList.remove('d-none');
        editElement.classList.add('d-none');
        // 显示编辑按钮
        editButton.classList.remove('d-none');
    }
}

// 保存总投入
async function saveTotalInvestment() {
    const input = document.getElementById('totalInvestmentInput');
    const newValue = parseFloat(input.value);
    const editButton = document.querySelector('button[onclick="toggleEdit(\'totalInvestment\')"]');
    
    if (isNaN(newValue) || newValue < 0) {
        showToast('请输入有效的金额', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/update_total_investment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                total_investment: newValue
            })
        });
        
        if (response.ok) {
            // 更新显示
            document.getElementById('totalInvestment').textContent = `¥${newValue.toFixed(2)}`;
            // 切换回显示模式
            toggleEdit('totalInvestment');
            // 显示编辑按钮
            editButton.classList.remove('d-none');
            // 重新加载数据以更新其他相关数值
            loadData();
            showToast('总投入更新成功', 'success');
        } else {
            throw new Error('更新失败');
        }
    } catch (error) {
        console.error('更新总投入失败:', error);
        showToast('更新失败: ' + error.message, 'error');
    }
}

// 取消编辑
function cancelEdit(elementId) {
    const displayElement = document.getElementById(`${elementId}Display`);
    const editElement = document.getElementById(`${elementId}Edit`);
    const editButton = document.querySelector(`button[onclick="toggleEdit('${elementId}')"]`);
    
    displayElement.classList.remove('d-none');
    editElement.classList.add('d-none');
    // 显示编辑按钮
    editButton.classList.remove('d-none');
}

// 更新库存价值
async function updateInventoryValue() {
    try {
        const response = await fetch('/api/update_inventory_value', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('更新失败');
        }
        
        const data = await response.json();
        
        if (data.success) {
            // 更新显示
            document.getElementById('currentValue').textContent = `¥${data.inventory_value.toFixed(2)}`;
            // 重新加载数据以更新其他相关数值
            loadData();
            showToast('库存价值更新成功', 'success');
        } else {
            throw new Error(data.error || '更新失败');
        }
    } catch (error) {
        console.error('更新库存价值失败:', error);
        showToast('更新失败: ' + error.message, 'error');
    }
}

// 更新总余额
async function updateTotalBalance() {
    try {
        const response = await fetch('/api/update_balance?platform=all', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('更新失败');
        }
        
        const data = await response.json();
        
        // 更新显示的余额
        updateBalanceDisplay(data);
        
        // 重新加载数据以更新其他相关数值
        loadData();
        
        showToast('总余额更新成功', 'success');
    } catch (error) {
        console.error('更新总余额失败:', error);
        showToast('更新失败: ' + error.message, 'error');
    }
}

// 加载Steam库存数据
function loadSteamInventory() {
    fetch('/api/steam_inventory')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('steamInventoryTableBody');
            tableBody.innerHTML = '';
            
            data.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${item.item_name}</td>
                    <td>${item.quantity}</td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('加载Steam库存失败:', error);
            alert('加载Steam库存失败，请检查控制台获取详细信息。');
        });
} 