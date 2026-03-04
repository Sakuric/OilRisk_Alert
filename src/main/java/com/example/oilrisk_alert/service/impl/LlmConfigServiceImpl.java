package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.config.LlmConfig;
import com.example.oilrisk_alert.service.LlmConfigService;
import com.example.oilrisk_alert.vo.LlmConfigVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class LlmConfigServiceImpl implements LlmConfigService {

    private final LlmConfig llmConfig;

    @Override
    public LlmConfigVO getConfig() {
        LlmConfigVO vo = new LlmConfigVO();
        vo.setProviderName(llmConfig.getProviderName());
        vo.setApiUrl(llmConfig.getApiUrl());
        vo.setApiKey(llmConfig.getMaskedKey());
        vo.setModel(llmConfig.getModel());
        return vo;
    }

    @Override
    public LlmConfigVO updateConfig(LlmConfigVO request) {
        if (request.getApiUrl() != null) {
            llmConfig.setApiUrl(request.getApiUrl());
        }
        if (request.getApiKey() != null && !request.getApiKey().contains("*")) {
            llmConfig.setApiKey(request.getApiKey());
        }
        if (request.getModel() != null) {
            llmConfig.setModel(request.getModel());
        }
        if (request.getProviderName() != null) {
            llmConfig.setProviderName(request.getProviderName());
        }
        return getConfig();
    }

    @Override
    public String getApiUrl() {
        return llmConfig.getApiUrl();
    }

    @Override
    public String getApiKey() {
        return llmConfig.getApiKey();
    }

    @Override
    public String getModel() {
        return llmConfig.getModel();
    }

    @Override
    public boolean hasApiKey() {
        String key = llmConfig.getApiKey();
        return key != null && !key.isEmpty();
    }
}
