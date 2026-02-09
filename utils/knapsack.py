def knapsack(items, max_weight):
    n = len(items)
    dp = [[0] * (max_weight + 1) for _ in range(n + 1)]

    # 填充 DP 数组
    for i in range(1, n + 1):
        weight = items[i - 1]['weight']
        value = items[i - 1]['value']
        for w in range(max_weight + 1):
            if weight <= w:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weight] + value)
            else:
                dp[i][w] = dp[i - 1][w]

    # 计算最大价值
    max_value = dp[n][max_weight]

    # 找出物品的选择情况
    w = max_weight
    selected_items = [0] * n  # 初始化选择状态

    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:  # 物品 i 被选择
            selected_items[i - 1] = 1
            w -= items[i - 1]['weight']

    return max_value, selected_items

if __name__ == '__main__':
    items = [{'weight': 10, 'value': 2}, {'weight': 8, 'value': 7}, {'weight': 8, 'value': 8}]
    max_weight = 20
    max_value, selected_items = knapsack(items, max_weight)
    print(f"最大价值: {max_value}")
    print(f"每个物品的选择情况: {selected_items}")  # 1 表示选择，0 表示不选择