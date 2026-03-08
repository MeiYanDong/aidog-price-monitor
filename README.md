# AIDOG 价格提醒器 / AIDOG Price Alert

## 中文说明

### 这是做什么的

这是一个用来监控 `AIDOG` 价格的小工具。

当价格低于设定值时，系统会自动通过飞书发送提醒消息，这样你不用一直盯盘，也能及时知道价格变化。

### 适合谁使用

如果你有这些需求，这个工具就适合你：

- 不想一直手动看价格
- 想在价格跌到某个位置时收到提醒
- 希望提醒直接发到飞书，方便随时查看

### 当前能做什么

当前版本主要完成一件事：

- 持续关注 `AIDOG` 的价格
- 当价格低于设定值时，自动发送飞书提醒

系统已经在云服务器上持续运行，平时不需要手动打开。

### 提醒是怎么工作的

当前版本采用的是“价格跌破提醒”：

- 当 AIDOG 价格低于目标价格时，系统会发送提醒
- 系统会定时检查价格
- 为了避免短时间内反复刷屏，提醒之间会有冷却时间

这意味着：

- 如果价格一直停留在低位，不会不停重复提醒
- 只有在满足提醒条件时，才会真正发出消息

### 你会收到什么

当提醒触发后，你会在飞书里看到一张卡片消息。

卡片里只保留最重要的信息：

- 当前价格
- 触发条件
- 提醒时间

整体目标是让你一眼就能看懂，不需要阅读复杂信息。

### 怎么使用

对普通使用者来说，使用流程很简单：

1. 确认飞书机器人已经配置好
2. 设定你想关注的价格
3. 等待系统自动监控
4. 当价格满足条件时，在飞书查看提醒

如果你已经收到过测试消息，说明提醒链路已经是通的。

### 怎么判断系统是否正常

你可以通过下面几种简单方式判断它是否在工作：

- 飞书能正常收到测试消息
- 价格达到条件后，飞书能收到提醒
- 系统一直保持运行状态

如果长时间没有提醒，不一定是系统异常，也可能只是价格还没有达到触发条件。

### 当前版本范围

为了先把流程跑通，当前版本做了收敛：

- 只监控 `AIDOG`
- 只保留“价格低于目标值”这一种提醒方式
- 提醒消息发送到飞书

### 一句话总结

不用一直盯盘，也能在 AIDOG 价格跌到关键位置时，第一时间通过飞书收到提醒。

---

## English Guide

### What This Project Does

This is a simple tool for monitoring the price of `AIDOG`.

When the price drops below a chosen level, the system automatically sends a Feishu alert, so you do not need to keep watching the market yourself.

### Who This Is For

This project is useful if you want to:

- stop checking the price manually all the time
- receive an alert when the price falls to a specific level
- get notifications directly in Feishu

### What It Does Right Now

The current version focuses on one job:

- keep tracking the price of `AIDOG`
- send a Feishu alert when the price falls below the target level

The system is already running continuously on a cloud server, so it does not need to be opened manually in daily use.

### How Alerts Work

The current version uses a price-below alert:

- when the AIDOG price falls below the target, an alert is sent
- the system checks the price regularly
- a cooldown is used to avoid repeated spam in a short period

This means:

- if the price stays low, the system will not keep sending the same alert again and again
- an alert is only sent when the condition is actually met

### What You Will Receive

When an alert is triggered, you will receive a Feishu card message.

The card only keeps the essential information:

- current price
- trigger condition
- alert time

The goal is to make the message easy to understand at a glance.

### How To Use It

For a non-technical user, the flow is simple:

1. Make sure the Feishu bot is ready
2. Set the price you want to watch
3. Let the system monitor automatically
4. Check Feishu when the alert condition is met

If you have already received a test message, the notification path is working.

### How To Know It Is Working

You can use these simple signs:

- test messages can be received in Feishu
- when the target price is reached, a real alert arrives
- the system keeps running in the background

If there is no alert for a long time, it does not automatically mean there is a problem. It may simply mean that the price has not reached the alert condition yet.

### Current Scope

To keep the first version simple, the project is intentionally limited:

- it only tracks `AIDOG`
- it only supports the price-below alert
- notifications are sent through Feishu

### One-Sentence Summary

You do not need to watch the market all the time. When AIDOG falls to an important price level, the system will notify you through Feishu.
