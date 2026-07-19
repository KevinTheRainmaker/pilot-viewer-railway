"""Create a C++17 task catalog equivalent to the Python experiment tasks."""

import json
import re
import sys
from pathlib import Path


CPP_STARTERS = {
    "S1-A": ("long long solution(std::vector<int> holes)", "long long solution(std::vector<int> holes) {\n    // TODO\n    return 0;\n}"),
    "S1-D": ("std::vector<Row> solution(const std::vector<Row>& rows, const std::vector<std::string>& wanted_ids)", "struct Row { std::string id; int value; };\n\nstd::vector<Row> solution(const std::vector<Row>& rows, const std::vector<std::string>& wanted_ids) {\n    // TODO\n    return {};\n}"),
    "S1-B": ("std::vector<int> solution(const std::vector<std::vector<int>>& lengths)", "std::vector<int> solution(const std::vector<std::vector<int>>& lengths) {\n    // BUG: 배치가 하나일 때 빈 결과를 반환합니다.\n    if (lengths.size() == 1) return {};\n    std::vector<int> result;\n    for (const auto& row : lengths) result.push_back(row[0]);\n    return result;\n}"),
    "S2-A": ("std::vector<int> solution(int n)", "std::vector<int> solution(int n) {\n    // TODO\n    return {};\n}"),
    "S2-D": ("std::vector<Result> solution(const std::vector<Source>& sources, const std::vector<Query>& queries)", "struct Source { int timestamp; int data; };\nstruct Query { int timestamp; int stuff; };\nstruct Result { int timestamp; int stuff; std::optional<int> data; };\n\nstd::vector<Result> solution(const std::vector<Source>& sources, const std::vector<Query>& queries) {\n    // TODO\n    return {};\n}"),
    "S2-B": ("std::vector<std::vector<double>> solution(const std::vector<std::vector<int>>& image)", "std::vector<std::vector<double>> solution(const std::vector<std::vector<int>>& image) {\n    std::vector<std::vector<double>> result;\n    for (const auto& row : image) {\n        std::vector<double> converted;\n        for (int pixel : row) {\n            // BUG: 정수 변환이 소수 부분을 버립니다.\n            converted.push_back(static_cast<int>(pixel / 127.5 - 1.0));\n        }\n        result.push_back(converted);\n    }\n    return result;\n}"),
    "S3-A": ("std::vector<int> solution(const std::vector<int>& changes)", "std::vector<int> solution(const std::vector<int>& changes) {\n    // TODO\n    return {};\n}"),
    "S3-D": ("std::vector<Row> solution(const std::vector<Row>& rows)", "using Value = std::variant<std::string, int, double, bool, std::monostate>;\nstruct Row { std::map<std::string, Value> values; };\n\nstd::vector<Row> solution(const std::vector<Row>& rows) {\n    // 문자열인지 확인: std::holds_alternative<std::string>(value)\n    // 문자열 가져오기: std::get<std::string>(value)\n    // TODO: 문자열 대안만 치환하고 나머지 대안은 보존하세요.\n    return {};\n}"),
    "S3-B": ("std::vector<std::string> solution(const std::set<std::string>& target_versions)", "std::vector<std::string> solution(const std::set<std::string>& target_versions) {\n    if (target_versions.empty()) return {\"py3\", \"py2_function_print\", \"py2\"};\n    bool all_py3 = std::all_of(target_versions.begin(), target_versions.end(), [](const std::string& v) { return v.rfind(\"py3\", 0) == 0; });\n    if (all_py3) return {\"py3\", \"py2_function_print\"};\n    // BUG: py2_function_print 후보가 누락되었습니다.\n    return {\"py2\"};\n}"),
    "S4-A": ("int solution(const std::vector<int>& targets, int center)", "int solution(const std::vector<int>& targets, int center) {\n    // TODO\n    return 0;\n}"),
    "S4-D": ("std::vector<int> solution(const std::vector<Value>& values)", "using Value = std::variant<int, double, std::string, bool, std::monostate>;\n\nstd::vector<int> solution(const std::vector<Value>& values) {\n    // TODO: int 대안으로 태그된 값만 반환하세요.\n    return {};\n}"),
    "S4-B": ("std::optional<Distribution> solution(const std::string& path, const std::string& data)", "struct Distribution { std::string name; std::optional<std::string> version; };\n\nstd::optional<Distribution> solution(const std::string& path, const std::string& data) {\n    // BUG: 최신 Kali가 사용하는 /etc/os-release를 확인하지 않습니다.\n    if (path == \"/etc/lsb-release\" && data.find(\"Kali\") != std::string::npos) {\n        std::regex pattern(R\"(DISTRIB_RELEASE=\\s*(.*?)\\s*(?:\\n|$))\");\n        std::smatch match;\n        if (std::regex_search(data, match, pattern)) return Distribution{\"Kali\", match[1].str()};\n        return Distribution{\"Kali\", std::nullopt};\n    }\n    return std::nullopt;\n}"),
}

CPP_NOTES = {
    "S1-D": "C++에서는 각 행을 `Row { string id; int value; }` 구조체로 제한합니다. 요청한 id 순서대로 행을 복사해 반환하세요.",
    "S2-D": "C++에서는 `Source`, `Query`, `Result` 구조체를 사용합니다. 해당 센서 값이 없을 때 `Result::data`는 `optional<int>`의 빈 값이어야 합니다.",
    "S3-D": "C++에서는 문자열·정수·실수·bool·값 없음이 들어갈 수 있는 `Value` variant를 사용합니다. 문자열 대안에만 `&LT;` 치환을 적용하세요.",
    "S4-D": "C++에서는 `Value` variant의 `int` 대안으로 태그된 값만 선택합니다. `bool`과 값 없음은 별도 대안입니다.",
    "S3-A": "음수 홀수의 반올림 후보를 계산할 때 C++의 `/`는 0 방향 절삭임에 유의하세요. 요구되는 내림·올림 후보를 명시적으로 계산해야 합니다.",
}

# This support is appended after participant code.  It intentionally accepts one
# JSON value per line, matching the Python catalog's execution contract.
CPP_JSON_SUPPORT = r'''
#include <bits/stdc++.h>
namespace runner {
struct J { enum K{N,B,X,S,A,O}; K k=N; bool b=false; std::string x,s; std::vector<J>a; std::map<std::string,J>o; };
struct P { const std::string& z; size_t i=0; void ws(){while(i<z.size()&&isspace((unsigned char)z[i]))++i;} char take(){ws();return i<z.size()?z[i++]:0;} J val(){ char c=take(); if(c=='"'){J q;q.k=J::S;while(i<z.size()&&z[i]!='"'){if(z[i]=='\\')++i;q.s+=z[i++];}++i;return q;} if(c=='['){J q;q.k=J::A;ws();if(i<z.size()&&z[i]==']'){++i;return q;}for(;;){q.a.push_back(val());ws();char d=z[i++];if(d==']')break;}return q;} if(c=='{'){J q;q.k=J::O;ws();if(i<z.size()&&z[i]=='}'){++i;return q;}for(;;){J key=val();take();q.o[key.s]=val();ws();char d=z[i++];if(d=='}')break;}return q;} --i; size_t st=i;while(i<z.size()&&!strchr(",]} \t\r\n",z[i]))++i;std::string t=z.substr(st,i-st);J q;if(t=="null")q.k=J::N;else if(t=="true"||t=="false"){q.k=J::B;q.b=t=="true";}else{q.k=J::X;q.x=t;}return q;} };
inline J read(){std::string l;std::getline(std::cin,l);return P{l}.val();} inline int integer(const J&v){return std::stoi(v.x);} inline double real(const J&v){return std::stod(v.x);} inline std::string str(const J&v){return v.s;} inline bool decimal(const J&v){return v.x.find_first_of(".eE")!=std::string::npos;}
inline std::vector<int> vi(const J&v){std::vector<int>r;for(auto&x:v.a)r.push_back(integer(x));return r;} inline std::vector<std::string> vs(const J&v){std::vector<std::string>r;for(auto&x:v.a)r.push_back(str(x));return r;} inline std::vector<std::vector<int>> vvi(const J&v){std::vector<std::vector<int>>r;for(auto&x:v.a)r.push_back(vi(x));return r;}
inline std::string esc(std::string s){std::string r;for(char c:s){if(c=='"'||c=='\\')r+='\\';r+=c;}return r;} inline std::string out(const std::string&s){return "\""+esc(s)+"\"";} inline std::string out(int x){return std::to_string(x);} inline std::string out(long long x){return std::to_string(x);} inline std::string out(double x){std::ostringstream q;q<<x;return q.str();} inline std::string out(bool x){return x?"true":"false";} inline std::string out(const std::monostate&){return "null";} template<class T> std::string out(const std::vector<T>&v){std::string r="[";for(size_t i=0;i<v.size();++i){if(i)r+=",";r+=out(v[i]);}return r+"]";}
}
'''


def cpp_runner(task_id):
    # Every main consumes exactly one JSON value per solution argument.
    runners = {
        "S1-A": "int main(){auto x=runner::vi(runner::read());std::cout<<runner::out(solution(x));}",
        "S1-B": "int main(){auto x=runner::vvi(runner::read());std::cout<<runner::out(solution(x));}",
        "S2-A": "int main(){auto x=runner::integer(runner::read());std::cout<<runner::out(solution(x));}",
        "S2-B": "int main(){auto x=runner::vvi(runner::read());std::cout<<runner::out(solution(x));}",
        "S3-A": "int main(){auto x=runner::vi(runner::read());std::cout<<runner::out(solution(x));}",
        "S3-B": "int main(){auto x=runner::vs(runner::read());std::set<std::string>s(x.begin(),x.end());std::cout<<runner::out(solution(s));}",
        "S4-A": "int main(){std::string line;std::getline(std::cin,line);std::istringstream in(line);std::vector<int>x;int value;while(in>>value)x.push_back(value);std::getline(std::cin,line);std::cout<<solution(x,std::stoi(line));}",
        "S1-D": "int main(){auto a=runner::read();std::vector<Row> r;for(auto&x:a.a)r.push_back({runner::str(x.o.at(\"id\")),runner::integer(x.o.at(\"value\"))});auto w=runner::vs(runner::read());auto z=solution(r,w);std::cout<<\"[\";for(size_t i=0;i<z.size();++i){if(i)std::cout<<\",\";std::cout<<\"{\\\"id\\\":\"<<runner::out(z[i].id)<<\",\\\"value\\\":\"<<z[i].value<<\"}\";}std::cout<<\"]\";}",
        "S2-D": "int main(){auto a=runner::read();std::vector<Source>s;for(auto&x:a.a)s.push_back({runner::integer(x.o.at(\"timestamp\")),runner::integer(x.o.at(\"data\"))});auto b=runner::read();std::vector<Query>q;for(auto&x:b.a)q.push_back({runner::integer(x.o.at(\"timestamp\")),runner::integer(x.o.at(\"stuff\"))});auto z=solution(s,q);std::cout<<\"[\";for(size_t i=0;i<z.size();++i){if(i)std::cout<<\",\";std::cout<<\"{\\\"timestamp\\\":\"<<z[i].timestamp<<\",\\\"stuff\\\":\"<<z[i].stuff<<\",\\\"data\\\":\"<<(z[i].data?std::to_string(*z[i].data):\"null\")<<\"}\";}std::cout<<\"]\";}",
        "S4-B": "int main(){auto p=runner::str(runner::read()),d=runner::str(runner::read());auto z=solution(p,d);if(!z)std::cout<<\"null\";else std::cout<<\"{\\\"name\\\":\"<<runner::out(z->name)<<\",\\\"version\\\":\"<<(z->version?runner::out(*z->version):\"null\")<<\"}\";}",
    }
    if task_id not in runners:
        # Variant-heavy tasks remain runnable; their function signature receives
        # JSON values translated to the declared alternatives.
        if task_id == "S4-D":
            return "int main(){std::string line;std::getline(std::cin,line);int count=std::stoi(line);std::vector<Value>v;for(int i=0;i<count;++i){std::getline(std::cin,line);std::istringstream in(line);std::string tag;in>>tag;if(tag==\"int\"){int x;in>>x;v.push_back(x);}else if(tag==\"double\"){double x;in>>x;v.push_back(x);}else if(tag==\"string\"){std::string x;std::getline(in>>std::ws,x);v.push_back(x);}else if(tag==\"bool\"){std::string x;in>>x;v.push_back(x==\"true\");}else if(tag==\"null\")v.push_back(std::monostate{});}std::cout<<runner::out(solution(v));}"
        if task_id == "S3-D":
            return "int main(){auto a=runner::read();std::vector<Row>r;for(auto&x:a.a){Row row;for(auto&kv:x.o){auto&v=kv.second;if(v.k==runner::J::S)row.values[kv.first]=v.s;else if(v.k==runner::J::B)row.values[kv.first]=v.b;else if(v.k==runner::J::N)row.values[kv.first]=std::monostate{};else if(runner::decimal(v))row.values[kv.first]=runner::real(v);else row.values[kv.first]=runner::integer(v);}r.push_back(row);}auto z=solution(r);std::cout<<\"[\";for(size_t i=0;i<z.size();++i){if(i)std::cout<<\",\";std::cout<<\"{\";bool f=true;for(auto&kv:z[i].values){if(!f)std::cout<<\",\";f=false;std::cout<<runner::out(kv.first)<<\":\";std::visit([](auto&&q){std::cout<<runner::out(q);},kv.second);}std::cout<<\"}\";}std::cout<<\"]\";}"
    return runners[task_id]


def main():
    source, output = map(Path, sys.argv[1:3])
    tasks = json.loads(source.read_text(encoding="utf-8"))
    converted = []
    for task in tasks:
        signature, starter = CPP_STARTERS[task["id"]]
        context = task["body_ko"].split("**함수 규격**", 1)[0].strip()
        context = re.sub(r"^\*\*사용 언어: Python\*\*\s*", "", context)
        context = (context.replace("딕셔너리", "구조체").replace("list", "vector")
                   .replace("None", "std::nullopt").replace("표준 라이브러리 `re`", "표준 `<regex>` 라이브러리"))
        if task["id"] == "S4-D":
            context = "외부 API 값은 C++ `Value` variant로 전달됩니다. int, double, string, bool, 값 없음 중 실제 int로 태그된 값만 원래 순서대로 추출하세요. C++에서는 int와 bool이 별도 variant 대안이므로, 이 문항은 Python의 bool-정수 상속 함정 대신 variant 타입 태그 판별을 평가합니다."
        if task["id"] == "S1-B":
            context = "음성 샘플의 유효 길이는 내부 벡터 하나에 정수 하나가 들어 있는 형태로 전달됩니다. 결과는 항상 `{5, 3, 8}` 같은 1차원 벡터여야 합니다. 그런데 현재 구현은 배치 크기가 1일 때 빈 벡터를 반환합니다. 이 때문에 요청이 한 건만 들어오면 유효 길이 정보가 사라지고, 이후 처리 단계에서 샘플 수와 길이 정보의 개수가 맞지 않게 됩니다."
        body = f"**사용 언어: C++17**\n\n{context}\n\n{CPP_NOTES.get(task['id'], '')}\n\n**C++17 함수 규격**\n```cpp\n{signature};\n```"
        converted.append({
            **{key: value for key, value in task.items() if key not in {"starter_code", "execution_runner", "body", "body_ko"}},
            "language": "cpp17",
            "body": body,
            "body_ko": body,
            "function_signature": signature,
            "starter_code": "#include <bits/stdc++.h>\nusing namespace std;\n\n" + starter,
            "execution_runner": CPP_JSON_SUPPORT + cpp_runner(task["id"]),
        })
    output.write_text(json.dumps(converted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
