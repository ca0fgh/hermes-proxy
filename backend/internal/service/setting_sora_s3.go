package service

import (
	"context"
	"fmt"
	"strconv"
)

// GetSoraS3Settings 读取 Sora 视频对象存储配置。
// 上游 v0.1.149 把 setting_service.go 拆成多个文件时不含本方法（Sora S3 存储为本仓特性）。
func (s *SettingService) GetSoraS3Settings(ctx context.Context) (*SoraS3Settings, error) {
	keys := []string{
		SettingKeySoraS3Enabled,
		SettingKeySoraS3Endpoint,
		SettingKeySoraS3Region,
		SettingKeySoraS3Bucket,
		SettingKeySoraS3AccessKeyID,
		SettingKeySoraS3SecretAccessKey,
		SettingKeySoraS3Prefix,
		SettingKeySoraS3ForcePathStyle,
		SettingKeySoraS3CDNURL,
		SettingKeySoraDefaultStorageQuotaBytes,
	}

	values, err := s.settingRepo.GetMultiple(ctx, keys)
	if err != nil {
		return nil, fmt.Errorf("get sora s3 settings: %w", err)
	}

	settings := &SoraS3Settings{
		Enabled:                   values[SettingKeySoraS3Enabled] == "true",
		Endpoint:                  values[SettingKeySoraS3Endpoint],
		Region:                    values[SettingKeySoraS3Region],
		Bucket:                    values[SettingKeySoraS3Bucket],
		AccessKeyID:               values[SettingKeySoraS3AccessKeyID],
		SecretAccessKey:           values[SettingKeySoraS3SecretAccessKey],
		SecretAccessKeyConfigured: values[SettingKeySoraS3SecretAccessKey] != "",
		Prefix:                    values[SettingKeySoraS3Prefix],
		ForcePathStyle:            values[SettingKeySoraS3ForcePathStyle] == "true",
		CDNURL:                    values[SettingKeySoraS3CDNURL],
	}
	if quota, parseErr := strconv.ParseInt(values[SettingKeySoraDefaultStorageQuotaBytes], 10, 64); parseErr == nil {
		settings.DefaultStorageQuotaBytes = quota
	}

	return settings, nil
}
