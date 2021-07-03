# General

`AWS Cloud9를 활용한 코딩교육` 세션 진행을 위해서 만든 스크립트입니다. 선생님과 학생이 새용할 IAM User와 Cloud9 프로젝트에 대한 생성 및 삭제에 대한 내용입니다. 급하게 만들다보니 유연한 사용은 어려울 수 있습니다.

# Requirement

## Install modules

`boto3`와 `PyInquirer`가 필요합니다.

```bash
python3 -m pip install boto3 PyInquirer
```

## Configuration

`configuration/configuration.json`에 어떻게 동작할지 설정을 할 수 있습니다. IAM Grop에 적용할 inline policy는 `policy` 디렉토리에 위치해야합니다.

# Usage

**IAM USER**

```bash
python3 iam-manager.py
```

**Cloud9 Project**

```bash
python3 cloud9-manager.py
```







