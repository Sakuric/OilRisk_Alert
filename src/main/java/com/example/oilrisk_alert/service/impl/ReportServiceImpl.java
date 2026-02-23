package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.entity.Alert;
import com.example.oilrisk_alert.mapper.AlertMapper;
import com.example.oilrisk_alert.service.ReportService;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Stream;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReportServiceImpl implements ReportService {

    private final AlertMapper alertMapper;
    private final ObjectMapper objectMapper;

    @Value("${llm.api.key:}")
    private String apiKey;

    @Value("${llm.api.url:https://api.deepseek.com/v1/chat/completions}")
    private String apiUrl;

    @Value("${llm.api.model:deepseek-chat}")
    private String apiModel;

    @Override
    public SseEmitter generateReport(Long alertId) {
        Alert alert = alertMapper.findById(alertId);
        if (alert == null) {
            throw new BusinessException(404, "Alert not found: " + alertId);
        }

        SseEmitter emitter = new SseEmitter(30_000L);
        AtomicBoolean completed = new AtomicBoolean(false);

        emitter.onTimeout(() -> {
            completed.set(true);
            log.warn("SSE emitter timed out for alert {}", alertId);
            emitter.complete();
        });
        emitter.onCompletion(() -> {
            completed.set(true);
        });

        if (alert.getAiReport() != null && !alert.getAiReport().isEmpty()) {
            streamCachedReport(emitter, alert.getAiReport(), completed);
        } else if (apiKey == null || apiKey.isEmpty()) {
            streamMockReport(emitter, alert, completed);
        } else {
            streamLlmReport(emitter, alert, completed);
        }

        return emitter;
    }

    private void streamCachedReport(SseEmitter emitter, String text, AtomicBoolean completed) {
        new Thread(() -> {
            try {
                int chunkSize = 4;
                for (int i = 0; i < text.length(); i += chunkSize) {
                    if (completed.get()) return;
                    String token = text.substring(i, Math.min(i + chunkSize, text.length()));
                    sendToken(emitter, token);
                    Thread.sleep(50);
                }
                if (!completed.get()) {
                    emitter.send(SseEmitter.event().data("[DONE]"));
                    emitter.complete();
                }
            } catch (Exception e) {
                if (!completed.get()) emitter.completeWithError(e);
            }
        }).start();
    }

    private void streamMockReport(SseEmitter emitter, Alert alert, AtomicBoolean completed) {
        new Thread(() -> {
            try {
                String mockText = String.format(
                        "根据%s的预警数据分析，当前原油市场风险指数为%.1f，处于%s风险等级。" +
                        "主要触发因素为%s，需要密切关注相关指标变化。" +
                        "建议及时调整风险管理策略，市场波动可能在未来一周内持续。" +
                        "综合多维度因子评估，当前市场不确定性较高，建议保持警惕。" +
                        "后续应持续跟踪供需、地缘政治及金融市场变化，做好风险应对准备。",
                        alert.getDate(), alert.getRiskIndex().doubleValue(),
                        alert.getLevel(), alert.getTriggerFactorZh());

                // Split into 5 chunks
                int chunkLen = mockText.length() / 5;
                for (int i = 0; i < 5; i++) {
                    if (completed.get()) return;
                    int start = i * chunkLen;
                    int end = (i == 4) ? mockText.length() : (i + 1) * chunkLen;
                    sendToken(emitter, mockText.substring(start, end));
                    Thread.sleep(50);
                }

                alertMapper.updateAiReport(alert.getId(), mockText);
                if (!completed.get()) {
                    emitter.send(SseEmitter.event().data("[DONE]"));
                    emitter.complete();
                }
            } catch (Exception e) {
                if (!completed.get()) emitter.completeWithError(e);
            }
        }).start();
    }

    private void streamLlmReport(SseEmitter emitter, Alert alert, AtomicBoolean completed) {
        new Thread(() -> {
            try {
                String systemPrompt = "你是原油市场风险分析专家。请根据提供的预警信息，生成200字左右的中文风险分析报告。";
                String userPrompt = String.format(
                        "预警日期：%s\n风险指数：%.1f\n风险等级：%s\n触发因子：%s（%s）\n" +
                        "请分析当前原油市场风险状况，给出专业建议。",
                        alert.getDate(), alert.getRiskIndex().doubleValue(),
                        alert.getLevel(), alert.getTriggerFactorZh(), alert.getTriggerFactor());

                String requestBody = objectMapper.writeValueAsString(Map.of(
                        "model", apiModel,
                        "messages", List.of(
                                Map.of("role", "system", "content", systemPrompt),
                                Map.of("role", "user", "content", userPrompt)
                        ),
                        "stream", true
                ));

                HttpClient client = HttpClient.newHttpClient();
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(apiUrl))
                        .header("Content-Type", "application/json")
                        .header("Authorization", "Bearer " + apiKey)
                        .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                        .build();

                HttpResponse<Stream<String>> response = client.send(request,
                        HttpResponse.BodyHandlers.ofLines());

                StringBuilder fullText = new StringBuilder();
                try (Stream<String> lines = response.body()) {
                    Iterator<String> it = lines.iterator();
                    while (it.hasNext() && !completed.get()) {
                        String line = it.next();
                        if (!line.startsWith("data: ")) continue;
                        String data = line.substring(6).trim();
                        if ("[DONE]".equals(data)) break;
                        try {
                            JsonNode node = objectMapper.readTree(data);
                            JsonNode content = node.at("/choices/0/delta/content");
                            if (!content.isMissingNode() && !content.isNull()) {
                                String token = content.asText();
                                fullText.append(token);
                                sendToken(emitter, token);
                            }
                        } catch (Exception ignored) {
                        }
                    }
                }

                String report = fullText.toString();
                if (!report.isEmpty()) {
                    alertMapper.updateAiReport(alert.getId(), report);
                }

                if (!completed.get()) {
                    emitter.send(SseEmitter.event().data("[DONE]"));
                    emitter.complete();
                }
            } catch (Exception e) {
                log.error("LLM streaming failed for alert {}", alert.getId(), e);
                try {
                    if (!completed.get()) emitter.completeWithError(e);
                } catch (Exception ignored) {
                }
            }
        }).start();
    }

    private void sendToken(SseEmitter emitter, String token) throws Exception {
        String json = objectMapper.writeValueAsString(Map.of("token", token));
        emitter.send(SseEmitter.event().data(json, MediaType.APPLICATION_JSON));
    }
}
